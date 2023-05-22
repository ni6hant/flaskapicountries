import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

app = FastAPI()

# Database Configuration
db_url = 'postgresql://flaskbloguser:WKNXpBOtYpcvtWBOpjMPFOAe1IgGuWWm@dpg-chgr2367avjbbjpntevg-a.oregon-postgres.render.com/flaskblogdb'
engine = create_engine(db_url)
Session = sessionmaker(bind=engine)
Base = declarative_base()

# Country Model
class Country(Base):
    __tablename__ = 'country'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    cca3 = db.Column(db.String)
    currency_code = db.Column(db.String)
    currency = db.Column(db.String)
    capital = db.Column(db.String)
    region = db.Column(db.String)
    subregion = db.Column(db.String)
    area = db.Column(db.BigInteger)
    map_url = db.Column(db.String)
    population = db.Column(db.BigInteger)
    flag_url = db.Column(db.String)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)
    neighbours = db.relationship('CountryNeighbours', backref='country', foreign_keys='CountryNeighbours.country_id')

class CountryNeighbours(Base):
    __tablename__ = 'country_neighbours'
    id = db.Column(db.Integer, primary_key=True)
    country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    neighbour_country_id = db.Column(db.Integer, db.ForeignKey('country.id'))
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

Base.metadata.create_all(engine)

# API endpoint to populate countries
@app.post('/populate_countries')
def populate_countries():
    response = requests.get('https://restcountries.com/v3.1/all')
    data = response.json()

    session = Session()

    for item in data:
        # Extract data from the item
        name = item['name']['common']
        cca3 = item['cca3']
        currencies = item.get('currencies', {})
        currency_data = next(iter(currencies.values()), {})
        currency_code = list(currencies)[0] if currencies else None
        currency = currency_data.get('name')
        capital = item.get('capital', [''])[0]
        region = item.get('region')
        subregion = item.get('subregion')
        area = item['area']
        map_url = item.get('maps', {}).get('googleMaps')
        population = item.get('population')
        flag_url = item['flags']['png']
        created_at = datetime.now()
        updated_at = datetime.now()

        # Create a new Country instance
        country = Country(
            name=name,
            cca3=cca3,
            currency_code=currency_code,
            currency=currency,
            capital=capital,
            region=region,
            subregion=subregion,
            area=area,
            map_url=map_url,
            population=population,
            flag_url=flag_url,
            created_at=created_at,
            updated_at=updated_at
        )

        # Add the country to the database session
        session.add(country)
        session.flush()  # Flush changes to get the auto-generated ID

        # Create country neighbors
        borders = item.get('borders', [])
        for neighbour_cca in borders:
            neighbour_country = session.query(Country).filter_by(cca3=neighbour_cca).first()
            if neighbour_country:
                country_neighbour = CountryNeighbours(
                    country_id=country.id,
                    neighbour_country_id=neighbour_country.id,
                    created_at=datetime.now(),
                    updated_at=datetime.now()
                )
                session.add(country_neighbour)

    # Commit the changes to the database
    session.commit()

    return 'Countries populated successfully!'

# API to return all the countries
@app.get('/country')
def get_all_countries(request: Request):
    sort_by = request.query_params.get('sort_by', 'a_to_z')
    page = int(request.query_params.get('page', 1))
    limit = int(request.query_params.get('limit', 10))
    name = request.query_params.get('name')
    region = request.query_params.get('region')
    subregion = request.query_params.get('subregion')

    session = Session()

    query = session.query(Country)

    if name:
        query = query.filter(Country.name.ilike(f'%{name}%'))
    if region:
        query = query.filter(Country.region.ilike(f'%{region}%'))
    if subregion:
        query = query.filter(Country.subregion.ilike(f'%{subregion}%'))

    total_count = query.count()
    total_pages = (total_count - 1) // limit + 1

    if sort_by == 'a_to_z':
        query = query.order_by(Country.name.asc())
    elif sort_by == 'z_to_a':
        query = query.order_by(Country.name.desc())
    elif sort_by == 'population_high_to_low':
        query = query.order_by(Country.population.desc())
    elif sort_by == 'population_low_to_high':
        query = query.order_by(Country.population.asc())
    elif sort_by == 'area_high_to_low':
        query = query.order_by(Country.area.desc())
    elif sort_by == 'area_low_to_high':
        query = query.order_by(Country.area.asc())

    paginated_query = query.paginate(page=page, per_page=limit)

    countries = []
    for country in paginated_query.items:
        countries.append({
            'id': country.id,
            'name': country.name,
            'cca3': country.cca3,
            'currency_code': country.currency_code,
            'currency': country.currency,
            'capital': country.capital,
            'region': country.region,
            'subregion': country.subregion,
            'area': country.area,
            'map_url': country.map_url,
            'population': country.population,
            'flag_url': country.flag_url,
        })

    response = {
        'countries': countries,
        'total_count': total_count,
        'total_pages': total_pages,
        'current_page': page,
        'limit': limit
    }

    return response

# API to get a country detail
@app.get('/country/{country_id}')
def get_country_detail(country_id: int):
    session = Session()
    country = session.query(Country).get(country_id)

    if country is None:
        return JSONResponse(
            status_code=404,
            content={
                'message': 'Country not found',
                'data': {}
            }
        )

    response = {
        'message': 'Country detail',
        'data': {
            'country': {
                'id': country.id,
                'name': country.name,
                'cca3': country.cca3,
                'currency_code': country.currency_code,
                'currency': country.currency,
                'capital': country.capital,
                'region': country.region,
                'subregion': country.subregion,
                'area': country.area,
                'map_url': country.map_url,
                'population': country.population,
                'flag_url': country.flag_url
            }
        }
    }

    return response

# API to get country neighbors
@app.get('/country/{country_id}/neighbour')
def get_country_neighbours(country_id: int):
    session = Session()
    country = session.query(Country).get(country_id)

    if country is None:
        return JSONResponse(
            status_code=404,
            content={
                'message': 'Country not found',
                'data': {}
            }
        )

    neighbours = session.query(Country).join(
        CountryNeighbours, Country.id == CountryNeighbours.neighbour_country_id
    ).filter(
        CountryNeighbours.country_id == country.id
    ).all()

    country_neighbours = []
    for neighbour in neighbours:
        country_neighbours.append({
            'id': neighbour.id,
            'name': neighbour.name,
            'cca3': neighbour.cca3,
            'currency_code': neighbour.currency_code,
            'currency': neighbour.currency,
            'capital': neighbour.capital,
            'region': neighbour.region,
            'subregion': neighbour.subregion,
            'area': neighbour.area,
            'map_url': neighbour.map_url,
            'population': neighbour.population,
            'flag_url': neighbour.flag_url,
        })

    response = {
        'message': 'Country neighbours',
        'data': {
            'countries': country_neighbours
        }
    }

    return response

# Create the database if it doesn't exist
Base.metadata.create_all(bind=engine)

# Create a FastAPI app instance
app = FastAPI()

# Mount the route handlers
app.include_router(api_router)

# Run the FastAPI application
if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
