import random
import psycopg2
import requests
import simplejson as json
from confluent_kafka import SerializingProducer
from tqdm import tqdm
import sys

BASE_URL = 'https://randomuser.me/api/?nat=gb'
PARTIES = ["ECORP Party", "SEP Party", "SV Party"]
NUM_VOTERS = 500

random.seed(12)
def create_tables(conn, cur):
    cur.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id VARCHAR(255) PRIMARY KEY,
                candidate_name VARCHAR(255),
                party_affiliation VARCHAR(255),
                biography TEXT,
                campaign_platform TEXT,
                photo_url TEXT
            )
        """)

    cur.execute("""
            CREATE TABLE IF NOT EXISTS voters (
                voter_id VARCHAR(255) PRIMARY KEY,
                voter_name VARCHAR(255),
                date_of_birth VARCHAR(255),
                gender VARCHAR(255),
                nationality VARCHAR(255),
                registration_number VARCHAR(255),
                address_street VARCHAR(255),
                address_city VARCHAR(255),
                address_state VARCHAR(255),
                address_country VARCHAR(255),
                address_postcode VARCHAR(255),
                email VARCHAR(255),
                phone_number VARCHAR(255),
                cell_number VARCHAR(255),
                picture TEXT,
                registered_age INTEGER
            )
        """)

    cur.execute("""
            CREATE TABLE IF NOT EXISTS votes (
                voter_id VARCHAR(255) UNIQUE,
                candidate_id VARCHAR(255),
                voting_time TIMESTAMP,
                vote int DEFAULT 1,
                PRIMARY KEY (voter_id, candidate_id)
            )
        """)

    conn.commit()

def generate_voter_data():
    response = requests.get(BASE_URL)
    if response.status_code == 200:
        user_data = response.json()['results'][0]
        return {
            "voter_id": user_data['login']['uuid'],
            "voter_name": f"{user_data['name']['first']} {user_data['name']['last']}",
            "date_of_birth": user_data['dob']['date'],
            "gender": user_data['gender'],
            "nationality": user_data['nat'],
            "registration_number": user_data['login']['username'],
            "address": {
                "street": f"{user_data['location']['street']['number']} {user_data['location']['street']['name']}",
                "city": user_data['location']['city'],
                "state": user_data['location']['state'],
                "country": user_data['location']['country'],
                "postcode": user_data['location']['postcode']
            },
            "email": user_data['email'],
            "phone_number": user_data['phone'],
            "cell_number": user_data['cell'],
            "picture": user_data['picture']['large'],
            "registered_age": user_data['registered']['age']
        }
    else:
        return "Error fetching data"

def generate_candidate_data(candidate_number, total_parties):
    # using the randomuser api to get random candidates
    response = requests.get(BASE_URL + '&gender=male')
    if response.status_code == 200:
        user_data = response.json()['results'][0]

        return {
            "candidate_id": user_data['login']['uuid'],
            "candidate_name": f"{user_data['name']['first']} {user_data['name']['last']}",
            "party_affiliation": PARTIES[candidate_number % total_parties],
            "biography": "A brief bio of the candidate.",
            "campaign_platform": "Key campaign promises or platform.",
            "photo_url": user_data['picture']['large']
        }
    else:
        return "Error fetching data"

def insert_voters(conn, cur, voter):
    cur.execute("""
                        INSERT INTO voters (voter_id, voter_name, date_of_birth, gender, nationality, registration_number, address_street, address_city, address_state, address_country, address_postcode, email, phone_number, cell_number, picture, registered_age)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s,%s,%s,%s,%s,%s)
                        """,
                (voter["voter_id"], voter['voter_name'], voter['date_of_birth'], voter['gender'],
                 voter['nationality'], voter['registration_number'], voter['address']['street'],
                 voter['address']['city'], voter['address']['state'], voter['address']['country'],
                 voter['address']['postcode'], voter['email'], voter['phone_number'],
                 voter['cell_number'], voter['picture'], voter['registered_age'])
                )
    conn.commit()

def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        pass
        #print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

if __name__ == "__main__":
    producer = SerializingProducer({'bootstrap.servers': 'broker:29092'})
    try:
        conn = psycopg2.connect("host=postgres dbname=voting user=postgres password=postgres")
        cur = conn.cursor()

        # creating the tables
        create_tables(conn, cur)

        # fetching the candidates
        cur.execute("""
            SELECT * FROM candidates;
        """)
        candidates = cur.fetchall()
        print(candidates)

        if len(candidates) == 0:
            for i in range(len(PARTIES)):
                candidate = generate_candidate_data(i, len(PARTIES))
                print(candidate)
                cur.execute("""
                                        INSERT INTO candidates (candidate_id, candidate_name, party_affiliation, biography, campaign_platform, photo_url)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """, (
                    candidate['candidate_id'], candidate['candidate_name'], candidate['party_affiliation'],
                    candidate['biography'],
                    candidate['campaign_platform'], candidate['photo_url']))
                conn.commit()
        with tqdm(total=NUM_VOTERS) as pbar:

            for i in range(NUM_VOTERS):
                try:
                    voter_data = generate_voter_data()
                    insert_voters(conn, cur, voter_data)

                    producer.produce(
                        "voters_topic",
                        key=voter_data["voter_id"],
                        value=json.dumps(voter_data),
                        on_delivery=delivery_report
                    )

                    
                    producer.flush()

                    pbar.set_description_str(f"Produced voter {i}, name: {voter_data['voter_name']}")
                    pbar.update(1)
                    
                except Exception as e:
                    print("Error: {}".format(e))
                    conn.rollback()
                    continue

    except Exception as e:
        print(e)

