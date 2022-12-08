from rest_framework import serializers
from django.contrib.auth import get_user_model
from slm.models import (
    Site,
    UserProfile,
    Agency,
    LogEntry,
    Alert,
    Network,
    ReviewRequest,
    SiteFileUpload
)
from slm import signals as slm_signals
from django.core.exceptions import PermissionDenied
from django.utils.timezone import now
import os


class EmbeddedAgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = [
            'id',
            'name',
            'country',
            'active'
        ]


class EmbeddedNetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = [
            'id',
            'name'
        ]


class EmbeddedUserSerializer(serializers.ModelSerializer):

    agency = EmbeddedAgencySerializer(many=False, required=False)

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'agency'
        ]


class StationSerializer(serializers.ModelSerializer):

    owner = EmbeddedUserSerializer(many=False, read_only=True)
    last_user = EmbeddedUserSerializer(many=False, read_only=True)
    agencies = EmbeddedAgencySerializer(many=True, read_only=True)
    networks = EmbeddedNetworkSerializer(many=True, read_only=True)

    can_publish = serializers.SerializerMethodField(read_only=True)

    publish = serializers.BooleanField(write_only=True)

    def get_can_publish(self, obj):
        if 'request' in self.context:
            return obj.can_publish(self.context['request'].user)
        return None

    def update(self, instance, validated_data):
        if validated_data.get('publish', False):
            instance.publish(request=self.context.get('request', None))
            # this might have been cached by an annotation - clear it in case
            # because publish may invalidate it
            if hasattr(instance, '_review_pending'):
                del instance._review_pending
        return instance

    def create(self, validated_data):
        # strip out anything but name or agencies
        validated_data = {
            key: val
            for key, val in validated_data.items()
            if key in {'name'}
        }

        validated_data['name'] = validated_data['name'].upper()
        new_site = super().create(validated_data)
        if not self.context['request'].user.is_superuser:
            new_site.agencies.add(self.context['request'].user.agency)

        slm_signals.site_proposed.send(
            sender=self,
            site=new_site,
            user=self.context['request'].user,
            timestamp=new_site.created,
            request=self.context['request'],
            agencies=new_site.agencies.all()
        )
        return new_site

    class Meta:
        model = Site
        fields = [
            'id',
            'name',
            'agencies',
            'networks',
            'created',
            'status',
            'owner',
            'num_flags',
            'last_publish',
            'last_update',
            'last_user',
            'can_publish',
            'publish',
            'review_pending'
        ]
        extra_kwargs = {
            field: {'read_only': True} for field in fields if field not in {
                'name', 'publish', 'owner', 'last_user',
                'agencies', 'networks', 'can_publish'
            }
        }


class ReviewRequestSerializer(serializers.ModelSerializer):

    site_name = serializers.CharField(source='site.name', required=True)
    site = StationSerializer(many=False, read_only=True)
    requester = EmbeddedUserSerializer(many=False, read_only=True)
    review_pending = None

    def create(self, validated_data):
        validated_data['requester'] = getattr(
            self.context['request'],
            'user',
            None
        )
        validated_data['site'] = Site.objects.get(
            name__iexact=validated_data['site']['name']
        )
        request = ReviewRequest.objects.update_or_create(
            site=validated_data['site'],
            defaults={
                'requester': validated_data['requester'],
                'timestamp': now()
            }
        )[0]
        request.refresh_from_db()
        self.review_pending = validated_data['site'].review_pending
        return request

    class Meta:
        model = ReviewRequest
        fields = ['site_name', 'site', 'requester', 'timestamp']


class LogEntrySerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name')
    user = EmbeddedUserSerializer(many=False)

    class Meta:
        model = LogEntry
        fields = [
            'type',
            'site',
            'timestamp',
            'user',
            'target',
            'epoch',
            'ip'
        ]
        read_only_fields = fields


class AlertSerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name', allow_null=True)
    user = EmbeddedUserSerializer(many=False)
    agency = EmbeddedAgencySerializer(many=False)

    class Meta:
        model = Alert
        fields = [
            'id',
            'level',
            'header',
            'detail',
            'timestamp',
            'sticky',
            'expires',
            'site',
            'user',
            'agency'
        ]
        read_only_fields = fields


class UserSerializer(serializers.ModelSerializer):

    agency = serializers.CharField(
        source='agency.name',
        allow_null=True,
        required=False
    )

    # profile fields
    phone1 = serializers.CharField(
        source='profile.phone1',
        allow_null=True
    )
    phone2 = serializers.CharField(
        source='profile.phone2',
        allow_null=True
    )
    address1 = serializers.CharField(
        source='profile.address1',
        allow_null=True
    )
    address2 = serializers.CharField(
        source='profile.address2',
        allow_null=True
    )
    address3 = serializers.CharField(
        source='profile.address3',
        allow_null=True
    )
    city = serializers.CharField(
        source='profile.city',
        allow_null=True
    )
    state_province = serializers.CharField(
        source='profile.state_province',
        allow_null=True
    )
    country = serializers.CharField(
        source='profile.country',
        allow_null=True
    )
    postal_code = serializers.CharField(
        source='profile.postal_code',
        allow_null=True
    )
    registration_agency = serializers.CharField(
        source='profile.registration_agency',
        allow_null=True
    )
    html_emails = serializers.BooleanField(
        source='profile.html_emails',
        allow_null=True
    )

    def update(self, instance, validated_data):

        if not hasattr(instance, 'profile') or instance.profile is None:
            UserProfile.objects.create(
                **{'user': instance, **validated_data.get('profile')}
            )
        else:
            for field, value in validated_data.get('profile', {}).items():
                setattr(instance.profile, field, value)
            instance.profile.save()

        for field, val in validated_data.items():
            if field != 'profile':
                setattr(instance, field, val)

        instance.save()
        return instance

    class Meta:
        model = get_user_model()
        fields = [
            'id',
            'email',
            'first_name',
            'last_name',
            'date_joined',
            'agency',
            'phone1',
            'phone2',
            'address1',
            'address2',
            'address3',
            'city',
            'state_province',
            'country',
            'postal_code',
            'registration_agency',
            'html_emails'
        ]
        read_only_fields = ('id', 'agency', 'date_joined')


class SiteFileUploadSerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name', allow_null=True)
    site_status = serializers.IntegerField(
        source='site.status',
        read_only=True
    )
    site_flags = serializers.IntegerField(
        source='site.num_flags',
        read_only=True
    )
    user = EmbeddedUserSerializer(many=False)

    class Meta:
        model = SiteFileUpload
        fields = [
            'id',
            'site',
            'site_status',
            'site_flags',
            'name',
            'user',
            'status',
            'timestamp',
            'file_type',
            'log_format',
            'mimetype',
            'description',
            'direction'
        ]
        read_only_fields = [
            field for field in fields
            if field not in {'status', 'name', 'description', 'direction'}
        ]
