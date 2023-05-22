from fastapi import FastAPI, Depends
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import requests
from sqlalchemy.orm import Session
from sqlalchemy_pagination import paginate
from sqlalchemy_pagination import paginate as paginate_query

# Create the FastAPI instance
app = FastAPI()

# Configure the database connection
DATABASE_URL = 'postgresql://flaskbloguser:WKNXpBOtYpcvtWBOpjMPFOAe1IgGuWWm@dpg-chgr2367avjbbjpntevg-a.oregon-postgres.render.com/flaskblogdb'
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# Country Model
class Country(Base):
    __tablename__ = 'country'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    cca3 = Column(String)
    currency_code = Column(String)
    currency = Column(String)
    capital = Column(String)
    region = Column(String)
    subregion = Column(String)
    area = Column(BigInteger)
    map_url = Column(String)
    population = Column(BigInteger)
    flag_url = Column(String)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    neighbours = relationship('CountryNeighbours', backref='country', foreign_keys='CountryNeighbours.country_id')

class CountryNeighbours(Base):
    __tablename__ = 'country_neighbours'
    id = Column(Integer, primary_key=True)
    country_id = Column(Integer, ForeignKey('country.id'))
    neighbour_country_id = Column(Integer, ForeignKey('country.id'))
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

# Create all tables in the database
Base.metadata.create_all(bind=engine)

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# API endpoint to populate countries
@app.post('/populate_countries')
def populate_countries():
    response = requests.get('https://restcountries.com/v3.1/all')
    data = response.json()

    with SessionLocal() as db:
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
            db.add(country)
            db.flush()  # Flush changes to get the auto-generated ID

            # Create country neighbors
            borders = item.get('borders', [])
            for neighbour_cca in borders:
                neighbour_country = db.query(Country).filter_by(cca3=neighbour_cca).first()
                if neighbour_country:
                    country_neighbour = CountryNeighbours(
                        country_id=country.id,
                        neighbour_country_id=neighbour_country.id,
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    db.add(country_neighbour)

        # Commit the changes to the database
        db.commit()

    return 'Countries populated successfully!'

# API to return all the countries
@app.get('/country')
def get_all_countries(
    sort_by: str = 'a_to_z',
    page: int = 1,
    limit: int = 10,
    name: str = None,
    region: str = None,
    subregion: str = None,
    db: Session = Depends(get_db)
):
    db = SessionLocal()
    query = db.query(Country)

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
    db.close()

# API to get a country detail
@app.get('/country/{country_id}')
def get_country_detail(country_id: int, db: Session = Depends(get_db)):
    country = db.query(Country).get(country_id)

    if country is None:
        return {
            'message': 'Country not found',
            'data': {}
        }

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
                'flag_url': country.flag_url,
            },
            'neighbours': []
        }
    }

    for neighbour in country.neighbours:
        neighbour_country = db.query(Country).get(neighbour.neighbour_country_id)
        response['data']['neighbours'].append({
            'id': neighbour_country.id,
            'name': neighbour_country.name,
            'cca3': neighbour_country.cca3,
            'currency_code': neighbour_country.currency_code,
            'currency': neighbour_country.currency,
            'capital': neighbour_country.capital,
            'region': neighbour_country.region,
            'subregion': neighbour_country.subregion,
            'area': neighbour_country.area,
            'map_url': neighbour_country.map_url,
            'population': neighbour_country.population,
            'flag_url': neighbour_country.flag_url,
        })

    return response


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)