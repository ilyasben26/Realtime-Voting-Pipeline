import time
import plotly.express as px
import numpy as np
import pandas as pd
import simplejson as json
import streamlit as st
from kafka import KafkaConsumer
from streamlit_autorefresh import st_autorefresh
import psycopg2

# Function to create a Kafka consumer
def create_kafka_consumer(topic_name):
    # Set up a Kafka consumer with specified topic and configurations
    consumer = KafkaConsumer(
        topic_name,
        bootstrap_servers='broker:29092',
        auto_offset_reset='earliest',
        value_deserializer=lambda x: json.loads(x.decode('utf-8')))
    return consumer

# Function to fetch voting statistics from PostgreSQL database
def fetch_voting_stats():
    # Connect to PostgreSQL database
    conn = psycopg2.connect("host=postgres dbname=voting user=postgres password=postgres")
    cur = conn.cursor()

    # Fetch total number of voters
    cur.execute("""
        SELECT count(*) voters_count FROM voters
    """)
    voters_count = cur.fetchone()[0]

    # Fetch total number of candidates
    cur.execute("""
        SELECT count(*) candidates_count FROM candidates
    """)
    candidates_count = cur.fetchone()[0]

    return voters_count, candidates_count

# Function to fetch data from Kafka
def fetch_data_from_kafka(consumer):
    # Poll Kafka consumer for messages within a timeout period
    messages = consumer.poll(timeout_ms=1000)
    data = []

    # Extract data from received messages
    for message in messages.values():
        for sub_message in message:
            data.append(sub_message.value)
    return data


# Function to update data displayed on the dashboard
def update_data():
    try:
        # Placeholder to display last refresh time
        last_refresh = st.empty()
        last_refresh.text(f"Last refreshed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # Fetch voting statistics
        voters_count, candidates_count = fetch_voting_stats()

        # Display total voters and candidates metrics
        st.markdown("""---""")
        col1, col2 = st.columns(2)
        col1.metric("Total Voters", voters_count)
        col2.metric("Total Candidates", candidates_count)

        # Fetch data from Kafka on aggregated votes per candidate
        consumer = create_kafka_consumer("aggregated_votes_per_candidate")
        data = fetch_data_from_kafka(consumer)
        results = pd.DataFrame(data)

        # Identify the leading candidate
        results = results.loc[results.groupby('candidate_id')['total_votes'].idxmax()]
        leading_candidate = results.loc[results['total_votes'].idxmax()]

        # Display leading candidate information
        st.markdown("""---""")
        st.header('Leading Candidate')
        col1, col2 = st.columns(2)
        with col1:
            st.image(leading_candidate['photo_url'], width=200)
        with col2:
            st.header(leading_candidate['candidate_name'])
            st.subheader(leading_candidate['party_affiliation'])
            st.subheader("Total Votes: {}".format(leading_candidate['total_votes']))

        # Display statistics and visualizations
        st.markdown("""---""")
        st.header('Statistics')
        results = results[['candidate_id', 'candidate_name', 'party_affiliation', 'total_votes']]
        results = results.reset_index(drop=True)
        col1, col2 = st.columns(2)

        # Display bar chart and donut chart
        with col1:
            bar_fig = px.bar(results, x='candidate_name', y='total_votes',
                                title='Total Votes per Candidate',
                                labels={
                                    "candidate_name": "Candidate",
                                    "total_votes": "Total votes"
                                })
            st.plotly_chart(bar_fig, use_container_width=True)

        with col2:
            pie_fig = px.pie(results, values='total_votes',names='candidate_name',
                                title='Voting Percentage per Candidate')
            st.plotly_chart(pie_fig, use_container_width=True)

        # Display table with candidate statistics
        st.table(results[['candidate_name','party_affiliation','total_votes']])

        # Fetch data from Kafka on aggregated turnout by location
        location_consumer = create_kafka_consumer("aggregated_turnout_by_location")
        location_data = fetch_data_from_kafka(location_consumer)
        location_result = pd.DataFrame(location_data)

        # Identify locations with maximum turnout
        location_result = location_result.loc[location_result.groupby('state')['count'].idxmax()]
        location_result = location_result.reset_index(drop=True)

        # Display location-based voter information with pagination
        st.header("Voters Turnout per State")
        st.dataframe(location_result, use_container_width=True, hide_index=True)

        # Update the last refresh time
        st.session_state['last_update'] = time.time()

    except Exception as e:
        st.warning("Data is still processing ...")
        st.warning(e)

# Sidebar layout
def sidebar():
    # Initialize last update time if not present in session state
    if st.session_state.get('last_update') is None:
        st.session_state['last_update'] = time.time()

    # Slider to control refresh interval
    refresh_interval = st.sidebar.slider("Refresh interval (seconds)", 5, 60, 10)
    st_autorefresh(interval=refresh_interval * 1000, key="auto")

    # Button to manually refresh data
    if st.sidebar.button('Refresh Data'):
        update_data()

# Title of the Streamlit dashboard
st.title('Real-time Elections Dashboard')
topic_name = 'aggregated_votes_per_candidate'

# Display sidebar
sidebar()

# Update and display data on the dashboard
update_data()