"""
Handles forms for site log sections, user
management.

There is a form for each sitelog section.

More info on forms:
https://docs.djangoproject.com/en/3.2/topics/forms/

More info on field types:
https://docs.djangoproject.com/en/3.2/ref/models/fields/
"""

from django import forms
from django.core.exceptions import FieldDoesNotExist
from django.core.validators import MinValueValidator
from django.db import transaction
from django.db.models import Max
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.urls import reverse_lazy
from django.db.models.fields import NOT_PROVIDED
from slm.api.edit.serializers import UserProfileSerializer, UserSerializer
from slm.defines import SLMFileType
from slm.widgets import (
    AutoComplete,
    SLMCheckboxSelectMultiple,
    SLMDateTimeWidget,
    DatePicker
)
from slm.models import (
    Agency,
    SatelliteSystem,
    Site,
    SiteAntenna,
    SiteCollocation,
    SiteFileUpload,
    SiteForm,
    SiteFrequencyStandard,
    SiteHumiditySensor,
    SiteIdentification,
    SiteLocalEpisodicEffects,
    SiteLocation,
    SiteMoreInformation,
    SiteMultiPathSources,
    SiteOperationalContact,
    SiteOtherInstrumentation,
    SitePressureSensor,
    SiteRadioInterferences,
    SiteReceiver,
    SiteResponsibleAgency,
    SiteSignalObstructions,
    SiteSurveyedLocalTies,
    SiteTemperatureSensor,
    SiteWaterVaporRadiometer,
)
from slm.utils import to_snake_case
from ckeditor.widgets import CKEditorWidget


class SLMDateField(forms.DateField):
    input_type = 'date'


class SLMTimeField(forms.TimeField):
    input_type = 'time'


class SLMDateTimeField(forms.SplitDateTimeField):

    widget = SLMDateTimeWidget

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.widgets[0].input_type = 'date'
        self.widget.widgets[1].input_type = 'time'


class NewSiteForm(forms.ModelForm):

    class Meta:
        model = Site
        fields = ['name', 'agencies']


class SectionForm(forms.ModelForm):

    def __init__(self, instance=None, **kwargs):
        self.diff = instance.published_diff() if instance else {}
        self.flags = instance._flags if instance else {}
        super().__init__(instance=instance, **kwargs)
        for field in self.fields:
            try:
                model_field = self.Meta.model._meta.get_field(field)
                self.fields[field].required = not (
                    getattr(model_field, 'default', None) != NOT_PROVIDED
                    and model_field.blank
                )
                self.fields[field].widget.attrs.setdefault('class', '')
                self.fields[field].widget.attrs['class'] += ' slm-form-field'
            except FieldDoesNotExist:
                pass

    @classmethod
    def section_name(cls):
        return to_snake_case(
            cls.Meta.model.__name__
        ).replace('_', ' ').replace('site', '').title().strip()

    @property
    def num_flags(self):
        return len(self.flags)

    @classmethod
    def api(cls):
        return f'slm_edit_api:{cls.Meta.model.__name__.lower()}'

    @cached_property
    def structured_fields(self):
        # todo this is spaghetti
        # arrange fields in structure to easily produce fieldsets in
        # correct order in the template, reflects old site
        # log order and groupings
        fields = []

        def flatten(structure):
            flat = []
            for field in structure:
                if isinstance(field, tuple) or isinstance(field, list):
                    flat += flatten(field)
                else:
                    flat.append(field)
            return flat

        def resolve_field(field_name):
            fields = []
            if field_name not in self.fields:
                if hasattr(getattr(self.Meta.model, field_name), 'field'):
                    field = getattr(self.Meta.model, field_name).field
                    if isinstance(field, tuple) or isinstance(field, list):
                        fields.extend([fd.name for fd in field])
                    else:
                        fields.append(field.name)
            else:
                fields.append(field_name)

            return [
                self.fields[field].get_bound_field(form=self, field_name=field)
                for field in fields
            ]

        for structure in self.Meta.model.structure():
            if isinstance(structure, tuple) or isinstance(structure, list):
                group_fields = []
                try:
                    self._meta.model._meta.get_field(structure[0])
                    group = None
                    group_fields.append(resolve_field(structure[0])[0])
                except FieldDoesNotExist:
                    group = structure[0]

                for field in flatten(structure[1]):
                    group_fields.extend(resolve_field(field))

                fields.append((group, group_fields))
            else:
                fields.append((None, resolve_field(structure)))
        fields += [(None, [field]) for field in self.hidden_fields()]
        return fields

    # todo this might be a security hole - restrict queryset to user's stations
    site = forms.ModelChoiceField(
        queryset=Site.objects.all(),
        widget=forms.HiddenInput()
    )

    id = forms.IntegerField(
        validators=[MinValueValidator(0)],
        widget=forms.HiddenInput(),
        required=False
    )

    class Meta:
        fields = ['site', 'id']


class SubSectionForm(SectionForm):

    subsection = forms.IntegerField(
        validators=[MinValueValidator(0)],
        widget=forms.HiddenInput(),
        required=False
    )

    def save(self, commit=True):
        if self.instance.subsection is None:
            with transaction.atomic():
                # todo is there a race condition here?
                self.instance.subsection = (
                    self.Meta.model.objects.select_for_update().filter(
                        site=self.instance.site
                    ).aggregate(Max('subsection'))['subsection__max'] or 0
                ) + 1

                return super().save(commit=commit)
        return super().save(commit=commit)

    @classmethod
    def group_name(cls):
        if hasattr(cls, 'NAV_HEADING'):
            return cls.NAV_HEADING.replace(
                ' ', '_'
            ).replace('.', '').strip().lower()
        return None

    class Meta(SectionForm.Meta):
        fields = [
            *SectionForm.Meta.fields,
            'subsection'
        ]


class SiteFormForm(SectionForm):

    class Meta(SectionForm.Meta):
        model = SiteForm
        fields = [
            *SectionForm.Meta.fields,
            *SiteForm.site_log_fields()
        ]
        widgets = {
            'date_prepared': DatePicker
        }


class SiteIdentificationForm(SectionForm):

    # we only include this for legacy purposes - this is not an editable value
    four_character_id = forms.CharField(
        label=_('Four Character ID'),
        help_text=_(
            'This is the 9 Character station name (XXXXMRCCC) used in RINEX 3 '
            'filenames. Format: (XXXX - existing four character IGS station '
            'name, M - Monument or marker number (0-9), R - Receiver number '
            '(0-9), CCC - Three digit ISO 3166-1 country code)'
        ),
        disabled=True,
        required=False
    )

    class Meta(SectionForm.Meta):
        model = SiteIdentification
        fields = [
            *SectionForm.Meta.fields,
            *SiteIdentification.site_log_fields(),
            'four_character_id'
        ]
        field_classes = {
            'date_installed': SLMDateTimeField
        }


class SiteLocationForm(SectionForm):

    class Meta:
        model = SiteLocation
        fields = [
            *SectionForm.Meta.fields,
            *SiteLocation.site_log_fields()
        ]


class SiteReceiverForm(SubSectionForm):

    satellite_system = forms.ModelChoiceField(
        queryset=SatelliteSystem.objects.all(),
        help_text=SiteReceiver._meta.get_field('satellite_system').help_text,
        label=SiteReceiver._meta.get_field('satellite_system').verbose_name,
        required=True,
        widget=SLMCheckboxSelectMultiple(columns=4),
        empty_label=None
    )

    receiver_type = forms.CharField(
        widget=AutoComplete(
            attrs={
                'data-service-url': reverse_lazy(
                    'slm_public_api:receiver-list'
                ),
                'data-param-name': 'model'
            }
        )
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # todo why is this not automatically done?
        if 'satellite_system' in self.initial:
            self.initial['satellite_system'] = [
                system.name for system in self.initial[
                    'satellite_system'
                ].all()
            ]

    class Meta(SubSectionForm):
        model = SiteReceiver
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteReceiver.site_log_fields()
        ]
        field_classes = {
            'installed': SLMDateTimeField,
            'removed': SLMDateTimeField
        }


class SiteAntennaForm(SubSectionForm):

    alignment = forms.FloatField(
        required=SiteAntenna._meta.get_field('alignment').blank,
        help_text=SiteAntenna._meta.get_field('alignment').help_text,
        label=SiteAntenna._meta.get_field('alignment').verbose_name,
        max_value=180,
        min_value=-180
    )

    antenna_type = forms.CharField(
        widget=AutoComplete(
            attrs={
                'data-service-url': reverse_lazy(
                    'slm_public_api:antenna-list'
                ),
                'data-param-name': 'model'
            }
        )
    )

    radome_type = forms.CharField(
        widget=AutoComplete(
            attrs={
                'data-service-url': reverse_lazy(
                    'slm_public_api:radome-list'
                ),
                'data-param-name': 'model'
            }
        )
    )

    class Meta(SubSectionForm):
        model = SiteAntenna
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteAntenna.site_log_fields()
        ]
        field_classes = {
            'installed': SLMDateTimeField,
            'removed': SLMDateTimeField
        }


class SiteSurveyedLocalTiesForm(SubSectionForm):

    class Meta(SubSectionForm.Meta):
        model = SiteSurveyedLocalTies
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteSurveyedLocalTies.site_log_fields()
        ]
        field_classes = {
            'measured': SLMDateTimeField
        }


class SiteFrequencyStandardForm(SubSectionForm):

    class Meta(SubSectionForm.Meta):
        model = SiteFrequencyStandard
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteFrequencyStandard.site_log_fields()
        ]
        widgets = {
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class SiteCollocationForm(SubSectionForm):

    class Meta(SubSectionForm.Meta):
        model = SiteCollocation
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteCollocation.site_log_fields()
        ]
        widgets = {
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class MeteorologicalForm(SubSectionForm):

    NAV_HEADING = _('Meteorological Instr.')

    class Meta(SubSectionForm):
        fields = SubSectionForm.Meta.fields
        widgets = {
            'calibration': DatePicker,
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class SiteHumiditySensorForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SiteHumiditySensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteHumiditySensor.site_log_fields()
        ]


class SitePressureSensorForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SitePressureSensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SitePressureSensor.site_log_fields()
        ]


class SiteTemperatureSensorForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SiteTemperatureSensor
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteTemperatureSensor.site_log_fields()
        ]


class SiteWaterVaporRadiometerForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SiteWaterVaporRadiometer
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteWaterVaporRadiometer.site_log_fields()
        ]


class SiteOtherInstrumentationForm(MeteorologicalForm):

    class Meta(MeteorologicalForm.Meta):
        model = SiteOtherInstrumentation
        fields = [
            *MeteorologicalForm.Meta.fields,
            *SiteOtherInstrumentation.site_log_fields()
        ]


class LocalConditionForm(SubSectionForm):

    NAV_HEADING = _('Local Conditions')

    class Meta(SubSectionForm.Meta):
        fields = SubSectionForm.Meta.fields
        widgets = {
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class SiteRadioInterferencesForm(LocalConditionForm):

    class Meta(LocalConditionForm.Meta):
        model = SiteRadioInterferences
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteRadioInterferences.site_log_fields()
        ]


class SiteMultiPathSourcesForm(LocalConditionForm):

    class Meta(LocalConditionForm.Meta):
        model = SiteMultiPathSources
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteMultiPathSources.site_log_fields()
        ]


class SiteSignalObstructionsForm(LocalConditionForm):

    class Meta(LocalConditionForm.Meta):
        model = SiteSignalObstructions
        fields = [
            *LocalConditionForm.Meta.fields,
            *SiteSignalObstructions.site_log_fields()
        ]


class SiteLocalEpisodicEffectsForm(SubSectionForm):

    class Meta(SubSectionForm.Meta):
        model = SiteLocalEpisodicEffects
        fields = [
            *SubSectionForm.Meta.fields,
            *SiteLocalEpisodicEffects.site_log_fields()
        ]
        widgets = {
            'effective_start': DatePicker,
            'effective_end': DatePicker
        }


class AgencyPOCForm(SectionForm):

    class Meta(SectionForm.Meta):
        fields = SectionForm.Meta.fields
        widgets = {
            'agency': forms.Textarea(attrs={'rows': 1}),
            'mailing_address': forms.Textarea(attrs={'rows': 4})
        }


class SiteOperationalContactForm(AgencyPOCForm):

    class Meta(AgencyPOCForm.Meta):
        model = SiteOperationalContact
        fields = [
            *AgencyPOCForm.Meta.fields,
            *SiteOperationalContact.site_log_fields()
        ]


class SiteResponsibleAgencyForm(AgencyPOCForm):

    class Meta(AgencyPOCForm.Meta):
        model = SiteResponsibleAgency
        fields = [
            *AgencyPOCForm.Meta.fields,
            *SiteResponsibleAgency.site_log_fields()
        ]


class SiteMoreInformationForm(SectionForm):

    class Meta(SectionForm.Meta):
        model = SiteMoreInformation
        fields = [
            *SectionForm.Meta.fields,
            *SiteMoreInformation.site_log_fields()
        ]


class UserForm(forms.ModelForm):

    agencies = forms.ModelMultipleChoiceField(
        queryset=Agency.objects.all(),
        required=False,
        disabled=True
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        if instance:
            self.fields['agencies'].queryset = instance.agencies.all()

    class Meta:
        model = UserSerializer.Meta.model
        fields = UserSerializer.Meta.fields
        exclude = ('date_joined', 'profile')


class UserProfileForm(forms.ModelForm):

    class Meta:
        model = UserProfileSerializer.Meta.model
        fields = UserProfileSerializer.Meta.fields


class SiteFileForm(forms.ModelForm):

    name = forms.SlugField(
        max_length=255,
        help_text=_('The name of the file.')
    )

    def __init__(self, *args, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)
        if instance and instance.file_type != SLMFileType.SITE_IMAGE:
            self.fields['direction'].widget = forms.HiddenInput()
            self.fields['direction'].disabled = True

    class Meta:
        model = SiteFileUpload
        fields = [
            'name',
            'description',
            'direction'
        ]


class RichTextForm(forms.Form):

    text = forms.CharField(widget=CKEditorWidget(config_name='richtextinput'))
