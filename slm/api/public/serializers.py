from rest_framework import serializers
from slm.models import (
    Agency,
    Network,
    SiteFileUpload,
    SiteIndex,
    Receiver,
    Antenna,
    Radome,
    ArchivedSiteLog
)
from slm.utils import build_absolute_url


class AntennaSerializer(serializers.ModelSerializer):

    manufacturer = serializers.CharField(
        source='manufacturer.name',
        allow_null=True
    )

    class Meta:
        model = Antenna
        fields = [
            'model',
            'description',
            'state',
            'manufacturer'
        ]


class ReceiverSerializer(serializers.ModelSerializer):

    manufacturer = serializers.CharField(
        source='manufacturer.name',
        allow_null=True
    )

    class Meta:
        model = Receiver
        fields = [
            'model',
            'description',
            'state',
            'manufacturer'
        ]


class RadomeSerializer(serializers.ModelSerializer):

    manufacturer = serializers.CharField(
        source='manufacturer.name',
        allow_null=True
    )

    class Meta:
        model = Radome
        fields = [
            'model',
            'description',
            'state',
            'manufacturer'
        ]


class EmbeddedAgencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Agency
        fields = [
            'name',
            'shortname',
            'country'
        ]


class EmbeddedNetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = [
            'name'
        ]


class StationListSerializer(serializers.ModelSerializer):

    name = serializers.CharField(source='site.name')
    last_publish = serializers.CharField(source='site.last_publish')
    agencies = EmbeddedAgencySerializer(source='site.agencies', many=True)
    networks = EmbeddedNetworkSerializer(source='site.networks', many=True)
    antenna_type = serializers.CharField(
        source='antenna.model',
        allow_null=True
    )
    radome_type = serializers.CharField(
        source='radome.model',
        allow_null=True
    )
    receiver_type = serializers.CharField(
        source='receiver.model',
        allow_null=True
    )
    registered = serializers.DateTimeField(source='site.created')
    last_rinex2 = serializers.DateTimeField()
    last_rinex3 = serializers.DateTimeField()
    last_rinex4 = serializers.DateTimeField()
    last_data_time = serializers.DateTimeField()
    last_data = serializers.SerializerMethodField()

    def get_last_data(self, obj):
        if obj.last_data:
            return max(0, obj.last_data.days)
        return None

    class Meta:
        model = SiteIndex
        fields = [
            'name',
            'agencies',
            'networks',
            'registered',
            'last_publish',
            'latitude',
            'longitude',
            'city',
            'country',
            'elevation',
            'antenna_type',
            'radome_type',
            'receiver_type',
            'serial_number',
            'firmware',
            'frequency_standard',
            'domes_number',
            'satellite_system',
            'data_center',
            'last_rinex2',
            'last_rinex3',
            'last_rinex4',
            'last_data_time',
            'last_data',
        ]


class SiteFileUploadSerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name', allow_null=True)
    download = serializers.SerializerMethodField()

    def get_download(self, obj):
        return build_absolute_url(
            obj.link,
            request=self.context.get('request', None)
        )

    class Meta:
        model = SiteFileUpload
        fields = [
            'id',
            'site',
            'name',
            'timestamp',
            'download',
            'mimetype',
            'description',
            'direction'
        ]
        read_only_fields = fields


class ArchiveSerializer(serializers.ModelSerializer):

    site = serializers.CharField(source='site.name', allow_null=True)

    class Meta:
        model = ArchivedSiteLog
        fields = [
            'id',
            'site',
            'name',
            'timestamp',
            'mimetype',
            'log_format',
            'size'
        ]
        read_only_fields = fields
