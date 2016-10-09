import uuid

from django.db import models
from django.db.models import Min, Avg
from django.utils.translation import ugettext as _
from django_extensions.db.models import TimeStampedModel

from constants import DIRECTIONALITY_CHOICES


class PlaceType(models.Model):
    class Meta:
        verbose_name = _('Place Type')
        verbose_name_plural = _('Place Types')

    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name


class Place(models.Model):

    class Meta:
        verbose_name = _('Place')
        verbose_name_plural = _('Places')

    code = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    type = models.ForeignKey(PlaceType)
    parentId = models.IntegerField(default=1)

    def __unicode__(self):
        return self.code + ": " + self.name + ' (' + self.type.__unicode__() + ')'

    def get_city(self):
        if self.type.name == 'City':
            return self
        places=Place.objects.filter(name=self.name.split()[0], type__name='City')
        if places.count() == 1:
            return places.first()
        return Place.objects.filter(name=' '.join(self.name.split()[:2]), type__name='City').first()


class Carrier(models.Model):

    class Meta:
        verbose_name = _('Carrier')
        verbose_name_plural = _('Carriers')

    code = models.CharField(max_length=10)
    display_code = models.CharField(max_length=10)
    name = models.CharField(max_length=200)
    image = models.URLField()

    def __unicode__(self):
        return self.display_code + ": " + self.name


class JourneyMode(models.Model):
    class Meta:
        verbose_name = _('Journey Mode')
        verbose_name_plural = _('Journey Modes')

    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name


class Segment(models.Model):

    class Meta:
        verbose_name = _('Segment')
        verbose_name_plural = _('Segments')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    departure_place = models.ForeignKey(Place, related_name='segment_departure_place')
    arrival_place = models.ForeignKey(Place, related_name='segment_arrival_place')
    departure = models.DateTimeField()
    arrival = models.DateTimeField()
    carrier = models.ForeignKey(Carrier, related_name='carrier')
    operating_carrier = models.ForeignKey(Carrier, related_name='operating_carrier')
    flight_number = models.CharField(max_length=10)
    duration = models.IntegerField(default=0)
    directionality = models.CharField(max_length=30, default='Outbound', choices=DIRECTIONALITY_CHOICES)
    journey_mode = models.ForeignKey(JourneyMode)

    def __unicode__(self):
        return self.departure_place.code + " - " + self.arrival_place.code


class Leg(models.Model):

    class Meta:
        verbose_name = _('Leg')
        verbose_name_plural = _('Legs')

    id = models.SlugField(primary_key=True, editable=False)
    departure_place = models.ForeignKey(Place, related_name='departure_place')
    arrival_place = models.ForeignKey(Place, related_name='arrival_place')
    departure = models.DateTimeField()
    arrival = models.DateTimeField()
    carriers = models.ManyToManyField(Carrier, related_name='carriers')
    operating_carriers = models.ManyToManyField(Carrier, related_name='operating_carriers')
    stops = models.ManyToManyField(Place, related_name='stops')
    duration = models.IntegerField(default=0)
    directionality = models.CharField(max_length=30, default='Outbound', choices=DIRECTIONALITY_CHOICES)
    journey_mode = models.ForeignKey(JourneyMode)
    segments = models.ManyToManyField(Segment)

    def __unicode__(self):
        ucode = self.departure_place.code + " - " + self.arrival_place.code
        if self.stops.count() != 0:
            ucode += " (" + _("Via") + ":"
            for stop in self.stops.all():
                ucode += " " + stop.code
            ucode += ")"
        else:
            ucode += " (" + _("Direct") + ")"
        return ucode


class AgentType(models.Model):

    class Meta:
        verbose_name = _('Agent Type')
        verbose_name_plural = _('Agent Types')

    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name


class Agent(models.Model):

    class Meta:
        verbose_name = _('Agent')
        verbose_name_plural = _('Agents')

    name = models.CharField(max_length=200)
    type = models.ForeignKey(AgentType)
    image = models.URLField()
    optimised_for_mobile = models.BooleanField(default=True)

    def __unicode__(self):
        return self.name


class FlightSearch(TimeStampedModel):

    class Meta:
        verbose_name = _('Flight Search')
        verbose_name_plural = _('Flight Searches')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    origin = models.CharField(max_length=30)
    destination = models.CharField(max_length=30)
    outbound = models.DateField()
    inbound = models.DateField()
    passengers = models.IntegerField(default=1)
    status = models.CharField(max_length=200)
    query = models.TextField()
    session_key = models.CharField(max_length=200)

    def __unicode__(self):
        return self.origin + '-' + self.destination + ' (' + self.outbound.strftime('%Y-%m-%d') + "-" + self.inbound.strftime('%Y-%m-%d') + ')'


    def get_origin_city(self):
        return self.itinerary_set.first().outbound_leg.departure_place.get_city()


    def get_destination_city(self):
        return self.itinerary_set.first().outbound_leg.arrival_place.get_city()

    def get_min_price(self):
        return self.itinerary_set.all().annotate(min_price=Min('pricingoption__price')).order_by(
            'min_price').first()

    def get_max_price(self):
        return self.itinerary_set.all().annotate(min_price=Min('pricingoption__price')).order_by(
            '-min_price').first()

    def get_mean_price(self):
        return \
            self.itinerary_set.all().annotate(min_price=Min('pricingoption__price')).aggregate(Avg('min_price'))[
                'min_price__avg']


class Itinerary(TimeStampedModel):

    class Meta:
        verbose_name = _('Itinerary')
        verbose_name_plural = _('Itineraries')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flight_search = models.ForeignKey(FlightSearch)
    inbound_leg = models.ForeignKey(Leg, related_name='inbound')
    outbound_leg = models.ForeignKey(Leg, related_name='outbound')
    booking_details_link = models.TextField()


class PricingOption(models.Model):

    class Meta:
        verbose_name = _('Pricing Option')
        verbose_name_plural = _('Pricing Options')

    itinerary = models.ForeignKey(Itinerary)
    price = models.FloatField()
    agents = models.ManyToManyField(Agent)
    deeplink = models.URLField(max_length=2000)
    quote_age_in_min = models.IntegerField(default=1)

    def get_agent(self):
        return self.agents.all().first().name
