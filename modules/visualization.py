"""
Visualization Module
Charts, graphs, maps, and timeline visualizations
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def render_visualization(case_id):
    """Render visualization interface"""
    st.header("Data Visualization")
    
    tabs = st.tabs(["Charts", "Location Map", "Timeline View", "Communication Network"])
    
    with tabs[0]:
        render_charts()
    
    with tabs[1]:
        render_location_map()
    
    with tabs[2]:
        render_timeline_view()
    
    with tabs[3]:
        render_communication_network()

def render_charts():
    """Render various data charts"""
    st.subheader("Data Analysis Charts")
    
    if 'call_logs' in st.session_state:
        st.write("**Call Activity Analysis**")
        
        call_logs = st.session_state['call_logs']
        
        call_type_counts = call_logs['Type'].value_counts()
        
        fig = px.pie(
            values=call_type_counts.values,
            names=call_type_counts.index,
            title="Call Distribution by Type"
        )
        st.plotly_chart(fig, width='stretch')
        
        call_logs['Hour'] = pd.to_datetime(call_logs['Timestamp']).dt.hour
        hourly_calls = call_logs.groupby('Hour').size()
        
        fig2 = px.bar(
            hourly_calls.reset_index(name='Count'),
            x='Hour',
            y='Count',
            labels={'Hour': 'Hour of Day', 'Count': 'Number of Calls'},
            title="Call Activity by Hour of Day"
        )
        st.plotly_chart(fig2, width='stretch')
    
    if 'sms_data' in st.session_state:
        st.write("**SMS Activity Analysis**")
        
        sms_data = st.session_state['sms_data']
        
        contact_counts = sms_data['Contact'].value_counts().head(10)
        
        contact_df = contact_counts.reset_index()
        contact_df.columns = ['Contact', 'Message Count']
        
        fig3 = px.bar(
            contact_df,
            x='Message Count',
            y='Contact',
            orientation='h',
            title="Top 10 Contacts by SMS Volume"
        )
        st.plotly_chart(fig3, width='stretch')
    
    if 'browser_history' in st.session_state:
        st.write("**Browser Activity Analysis**")
        
        history = st.session_state['browser_history']
        top_sites = history['Title'].value_counts().head(10)
        
        top_sites_df = top_sites.reset_index()
        top_sites_df.columns = ['Website', 'Visit Count']
        
        fig4 = px.bar(
            top_sites_df,
            x='Website',
            y='Visit Count',
            title="Top 10 Most Visited Websites"
        )
        fig4.update_xaxes(tickangle=45)
        st.plotly_chart(fig4, width='stretch')

def render_location_map():
    """Render location data on a map"""
    st.subheader("Location History Map")
    
    if 'locations' in st.session_state:
        locations = st.session_state['locations']
        
        fig = px.scatter_mapbox(
            locations,
            lat='Latitude',
            lon='Longitude',
            color='Source',
            size='Accuracy (m)',
            hover_data=['Timestamp', 'Accuracy (m)'],
            title="Device Location History",
            zoom=10,
            height=600
        )
        
        fig.update_layout(
            mapbox_style="open-street-map",
            margin={"r":0,"t":40,"l":0,"b":0}
        )
        
        st.plotly_chart(fig, width='stretch')
        
        st.metric("Total Location Points", len(locations))
        
        st.dataframe(locations, width='stretch')
    
    else:
        st.info("No location data extracted yet. Extract location data from the 'Data Extraction' tab first.")
        
        st.write("**Location data can come from:**")
        st.write("- GPS coordinates in photo EXIF data")
        st.write("- Google Maps location history")
        st.write("- Cell tower triangulation logs")
        st.write("- WiFi access point locations")

def render_timeline_view():
    """Render visual timeline"""
    st.subheader("Visual Timeline")
    
    if 'timeline' in st.session_state:
        timeline = st.session_state['timeline']
        
        timeline['Date'] = pd.to_datetime(timeline['Timestamp']).dt.date
        daily_events = timeline.groupby(['Date', 'Type']).size().reset_index(name='Count')
        
        fig = px.line(
            daily_events,
            x='Date',
            y='Count',
            color='Type',
            title="Event Activity Over Time",
            markers=True
        )
        
        st.plotly_chart(fig, width='stretch')
        
        event_distribution = timeline['Type'].value_counts()
        
        event_df = event_distribution.reset_index()
        event_df.columns = ['Event Type', 'Count']
        
        fig2 = px.bar(
            event_df,
            x='Event Type',
            y='Count',
            title="Distribution of Events by Type"
        )
        st.plotly_chart(fig2, width='stretch')
    
    else:
        st.info("No timeline generated yet. Generate a timeline from the 'Analysis Tools' tab first.")

def render_communication_network():
    """Render communication network graph"""
    st.subheader("Communication Network")
    
    st.info("Visualize relationships between contacts based on communication frequency")
    
    contacts_data = []
    
    if 'call_logs' in st.session_state:
        call_contacts = st.session_state['call_logs']['Contact'].value_counts()
        for contact, count in call_contacts.items():
            contacts_data.append({"Contact": contact, "Calls": count, "SMS": 0})
    
    if 'sms_data' in st.session_state:
        sms_contacts = st.session_state['sms_data']['Contact'].value_counts()
        for contact, count in sms_contacts.items():
            found = False
            for item in contacts_data:
                if item['Contact'] == contact:
                    item['SMS'] = count
                    found = True
                    break
            if not found:
                contacts_data.append({"Contact": contact, "Calls": 0, "SMS": count})
    
    if contacts_data:
        df = pd.DataFrame(contacts_data)
        df['Total'] = df['Calls'] + df['SMS']
        df = df.sort_values('Total', ascending=False).head(15)
        
        fig = px.scatter(
            df,
            x='Calls',
            y='SMS',
            size='Total',
            text='Contact',
            title="Contact Communication Matrix",
            labels={'Calls': 'Total Calls', 'SMS': 'Total SMS Messages'}
        )
        
        fig.update_traces(textposition='top center')
        st.plotly_chart(fig, width='stretch')
        
        st.dataframe(df, width='stretch')
    
    else:
        st.info("Extract call logs and SMS data first to visualize the communication network")
