# coding=utf-8
from django.contrib import admin

from skyscannerSDK.models import Place, Carrier, Leg, FlightSearch, Agent, Segment, PricingOption, Itinerary


class PricingOptionInline(admin.StackedInline):
    model = PricingOption
    extra = 0
    filter_horizontal = ('agents',)


class ItineraryInline(admin.StackedInline):
    model = Itinerary
    extra = 0


class PlaceAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name', 'type')


class CarrierAdmin(admin.ModelAdmin):
    list_display = ('id', 'display_code', 'name')


class LegAdmin(admin.ModelAdmin):
    list_display = ('id', 'departure_place', 'arrival_place', 'departure', 'arrival', 'count_stops', 'flight_duration')
    filter_horizontal = ('segments', 'carriers', 'operating_carriers', 'stops')
    search_fields = ('departure_place__name', 'arrival_place__name')

    def count_stops(self, obj):
        return obj.stops.count()

    def flight_duration(self, obj):
        return str(obj.duration/60) + "h " + str(obj.duration%60) + "min"


class SegmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'departure_place', 'arrival_place', 'departure', 'arrival', 'carrier', 'flight_number', 'flight_duration')

    def flight_duration(self, obj):
        return str(obj.duration / 60) + "h " + str(obj.duration % 60) + "min"


class ItineraryAdmin(admin.ModelAdmin):
    list_display = ('id', 'inbound_leg', 'outbound_leg', 'min_price')
    inlines = (PricingOptionInline,)

    def min_price(self, obj):
        return str(obj.pricingoption_set.all().first().price) + "€"


class FlightSearchAdmin(admin.ModelAdmin):
    list_display = ('id', 'origin', 'destination', 'outbound', 'inbound', 'created')
    inlines = (ItineraryInline,)
    date_hierarchy = 'created'
    list_filter = ('origin', 'destination')


class AgentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'type', 'optimised_for_mobile')
    list_filter = ('type', 'optimised_for_mobile')


admin.site.register(Place, PlaceAdmin)
admin.site.register(Carrier, CarrierAdmin)
admin.site.register(Leg, LegAdmin)
admin.site.register(Segment, SegmentAdmin)
admin.site.register(Itinerary, ItineraryAdmin)
admin.site.register(FlightSearch, FlightSearchAdmin)
admin.site.register(Agent, AgentAdmin)