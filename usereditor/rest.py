from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models.expressions import Value
from django.db.models.functions import Coalesce, Concat
from django.utils.translation import ugettext_lazy as _
from dynamicforms_legacy import fields, serializers, viewsets
from dynamicforms_legacy.action import Actions
from dynamicforms_legacy.mixins import DisplayMode
from rest_framework import routers
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response


class UserEmailField(fields.EmailField):

    def to_representation(self, value, row_data=None):
        res = super().to_representation(getattr(value, 'email', '') or '', row_data)
        email, verified = self.parent.get_email(value)
        return email or res

    def to_internal_value(self, data):
        return dict(email=super().to_internal_value(data))

    def run_validators(self, value):
        return super().run_validators(value['email'])


class UserSerializer(serializers.ModelSerializer):
    form_template = 'usereditor/user_item.html'
    form_titles = {
        'table': _('Users'),
        'new': _('New user'),
        'edit': _('Editing user'),
    }
    actions = Actions(add_default_crud=True, add_default_filter=True)
    show_filter = True

    password = fields.CharField(label=_('Password'), write_only=True, display_table=fields.DisplayMode.SUPPRESS)
    full_name = fields.SerializerMethodField(label=_('Full name'), read_only=True,
                                             display_form=fields.DisplayMode.SUPPRESS)
    username = fields.CharField(label=_('Username'), display_table=fields.DisplayMode.SUPPRESS)
    email = UserEmailField(label=_('Email'), source='*', required=False, allow_blank=True)
    email_verified = fields.SerializerMethodField(display_table=fields.DisplayMode.SUPPRESS)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def suppress_action(self, action, request, viewset):
        if request and request.user and not request.user.is_staff and action.name in ('add', 'edit', 'delete'):
            return True
        return super().suppress_action(action, request, viewset)

    def get_email(self, obj):
        email = None
        if hasattr(obj, 'emailaddress_set'):
            for e in obj.emailaddress_set.all():
                if e.verified and (not email or e.email == obj.email):
                    # email mora biti verificiran, da povozi onega iz userja,
                    #   če pa je še enak za povrh, je pa sploh super
                    email = e

            if email:
                return email.email, email.verified

        return None, False

    def get_full_name(self, obj):
        if not obj.id:
            return ''
        return obj.get_full_name()

    def validate(self, attrs):
        res = super().validate(attrs)
        email = attrs.get('email', None)
        if not email:
            return res

        from allauth.account.models import EmailAddress
        from rest_framework.exceptions import ValidationError

        qry = EmailAddress.objects.filter(email=email)
        if self.instance:
            qry = qry.exclude(user=self.instance)
        if qry.exists():
            raise ValidationError(dict(email=_('This e-mail address is already associated with another account.')))

        return res

    @transaction.atomic
    def create(self, validated_data):
        res = super().create(validated_data)
        self.update_user_settings(res, validated_data)
        return res

    @transaction.atomic
    def update(self, instance, validated_data):
        # noinspection PyTypeChecker
        self.update_user_settings(instance, validated_data)
        return super().update(instance, validated_data)

    @staticmethod
    def update_user_settings(instance, validated_data, *args, **kwargs):
        from allauth.account.models import EmailAddress

        email = validated_data.get('email', None)
        if email and not EmailAddress.objects.filter(user=instance, email=email).exists():
            EmailAddress.objects.filter(user=instance).update(primary=False)
            EmailAddress.objects.create(user=instance, email=email, primary=True, verified=False)

    def get_email_verified(self, rec):
        return self.get_email(rec)[1]

    class Meta:
        model = get_user_model()
        fields = ('id', 'full_name', 'username', 'password', 'first_name', 'last_name', 'is_staff', 'is_superuser',
                  'is_active', 'email', 'email_verified')
        changed_flds = {
            'id': dict(display=DisplayMode.HIDDEN),
        }
        for f in ['first_name', 'last_name', 'is_superuser', 'is_active']:  # type: fields.RenderMixin
            changed_flds[f] = dict(display_table=DisplayMode.SUPPRESS)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = (IsAdminUser,)

    queryset = get_user_model().objects.exclude(username__in=('admin',)) \
        .annotate(un=Concat(Coalesce('first_name', Value('')), Value(' '), Coalesce('last_name', 'username'))) \
        .prefetch_related('emailaddress_set') \
        .all()

    template_context = dict(url_reverse='usersitem', dialog_classes='modal-lg', dialog_header_classes='bg-info')
    pagination_class = viewsets.ModelViewSet.generate_paged_loader(ordering=['un'])

    def filter_queryset_field(self, queryset, field, value):
        if field == 'full_name':
            return queryset.filter(un__icontains=value)
        return super().filter_queryset_field(queryset, field, value)

    def perform_create(self, serializer):
        serializer.save()
        serializer.instance.set_password(serializer.validated_data.get('password', ''))
        serializer.instance.save()

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        pwd = request.data.get('password', None)
        instance = self.get_object()
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True
        request.data['password'] = instance.password
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        # Following code is because 'source' for email Field is '*'. Which means that serializer uses whole User
        # instance. And in that case when you update to blank value field just get ignored.
        if request.data.get('email', None) == '':
            serializer._validated_data['email'] = ''

        self.perform_update(serializer)
        if pwd:
            instance.set_password(pwd)
            instance.save()
        return Response(serializer.data)


# Routers provide a way of automatically determining the URL conf.
router = routers.DefaultRouter()
router.register(r'rest/users', UserViewSet, 'usersitem')
