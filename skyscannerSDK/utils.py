from django.utils.dateparse import parse_datetime
from pytz import UTC
from skyscanner.skyscanner import Flights

from constants import API_KEY, MARKET, CURRENCY, LOCALE
from skyscannerSDK.models import Place, PlaceType, FlightSearch, Carrier, Agent, AgentType, Leg, JourneyMode, Segment, \
    Itinerary, PricingOption


def search_flights(origin, destination, outbound, inbound, passengers):
    flights_service = Flights(API_KEY)
    result = flights_service.get_result(
        country=MARKET,
        currency=CURRENCY,
        locale=LOCALE,
        originplace=origin,
        destinationplace=destination,
        outbounddate=outbound.strftime('%Y-%m-%d'),
        inbounddate=inbound.strftime('%Y-%m-%d'),
        adults=passengers)

    if result.status_code is 200:
        fs = FlightSearch.objects.create(
            origin=origin,
            destination=destination,
            outbound=outbound,
            inbound=inbound,
            passengers=passengers,
            status=result.parsed['Status'],
            query=result.parsed['Query'],
            session_key=result.parsed['SessionKey']
        )
        return format_flight_search(fs, result.parsed)
    else:
        raise SearchErrorException(result.status_code)


def format_flight_search(flight_search, result):

    update_places(result)
    update_carriers(result)
    update_agents(result)
    get_legs(result)
    get_itineraries(result, flight_search)

    return flight_search


def update_places(result):

    places = result['Places']

    for place in places:
        if not Place.objects.filter(pk=place['Id']):
            Place.objects.create(
               id = place['Id'],
               code = place['Code'],
               name = place['Name'],
               type = PlaceType.objects.get_or_create(name=place['Type'])[0],
               parentId = place.get('parentId', 0),
            )


def update_carriers(result):

    carriers = result['Carriers']

    for carrier in carriers:
        if not Carrier.objects.filter(pk=carrier['Id']):
            Carrier.objects.create(
                id=carrier['Id'],
                code=carrier['Code'],
                display_code=carrier['DisplayCode'],
                name=carrier['Name'],
                image=carrier['ImageUrl']
            )


def update_agents(result):

    agents = result['Agents']

    for agent in agents:
        if not Agent.objects.filter(pk=agent['Id']):
            Agent.objects.create(
                id = agent['Id'],
                image = agent['ImageUrl'],
                name = agent['Name'],
                type = AgentType.objects.get_or_create(name=agent['Type'])[0],
                optimised_for_mobile= agent['OptimisedForMobile'],
            )


def get_legs(result):

    legs = result['Legs']
    segments = result['Segments']

    for leg in legs:

        l, created = Leg.objects.get_or_create(
            id = leg['Id'],
            departure_place = Place.objects.get(pk=leg['OriginStation']),
            arrival_place = Place.objects.get(pk=leg['DestinationStation']),
            departure = UTC.localize(parse_datetime(leg['Departure']), is_dst=True),
            arrival =  UTC.localize(parse_datetime(leg['Arrival']), is_dst=True),
            duration = leg['Duration'],
            directionality = leg['Directionality'],
            journey_mode = JourneyMode.objects.get_or_create(name=leg['JourneyMode'])[0]
        )

        carriers = leg['Carriers']
        ocarriers = leg['OperatingCarriers']
        stops = leg['Stops']
        lsegments = leg['SegmentIds']

        for carrier in carriers:
            l.carriers.add(Carrier.objects.get(pk=carrier))

        for ocarrier in ocarriers:
            l.operating_carriers.add(Carrier.objects.get(pk=ocarrier))

        for stop in stops:
            if stop != 0:
                l.stops.add(Place.objects.get(pk=stop))

        for lsegment in lsegments:
            l.segments.add(update_segment(lsegment, segments))

        l.save()


def update_segment(lsegment, segments):
    s = find(lsegment, segments)

    segment, created=Segment.objects.get_or_create(
        departure_place=Place.objects.get(pk=s['OriginStation']),
        arrival_place=Place.objects.get(pk=s['DestinationStation']),
        departure=UTC.localize(parse_datetime(s['DepartureDateTime']), is_dst=True),
        arrival=UTC.localize(parse_datetime(s['ArrivalDateTime']), is_dst=True),
        duration=s['Duration'],
        directionality=s['Directionality'],
        journey_mode=JourneyMode.objects.get_or_create(name=s['JourneyMode'])[0],
        flight_number=s['FlightNumber'],
        carrier=Carrier.objects.get(pk=s['Carrier']),
        operating_carrier=Carrier.objects.get(pk=s['OperatingCarrier'])
    )

    return segment


def find(value, dict):
    for d in dict:
        if d.get('Id', None) == value:
            return d


def get_itineraries(result, flight_search):
    itineraries = result['Itineraries']

    for itinerary in itineraries:
        i = Itinerary.objects.create(
            flight_search=flight_search,
            inbound_leg=Leg.objects.get(id=itinerary['InboundLegId']),
            outbound_leg=Leg.objects.get(id=itinerary['OutboundLegId']),
            booking_details_link=itinerary['BookingDetailsLink']
        )

        pricing_options = itinerary['PricingOptions']

        for option in pricing_options:
            p = PricingOption.objects.create(
                itinerary=i,
                price=option['Price'],
                deeplink=option['DeeplinkUrl'],
                quote_age_in_min=option['QuoteAgeInMinutes']
            )

            agents = option['Agents']

            for agent in agents:
                p.agents.add(Agent.objects.get(pk=agent))

            p.save()


class SearchErrorException(Exception):
    pass