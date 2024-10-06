import streamlit as st
import time

# Initialize session state variables to manage updates
if "start_point" not in st.session_state:
    st.session_state["start_point"] = None
if "end_point" not in st.session_state:
    st.session_state["end_point"] = None
if "last_update_time" not in st.session_state:
    st.session_state.last_update_time = 0

# Function to simulate fetching data every second
def fetch_truck_value():
    return 500

def fetch_motorbike_value():
    return 100

def fetch_car_value():
    return 300

def fetch_total_vehicles_value():
    return 900

# Set the Google Maps API Key (Replace 'YOUR_GOOGLE_MAPS_API_KEY' with your actual key)
GOOGLE_MAPS_API_KEY = 'AIzaSyBvsVrsscV50q6bVV7ofEm2tzCz08F1k1A'

# Create 4 columns for the dashboard
col1, col2, col3, col4 = st.columns(4)

# Create placeholders for the metrics in each column
truck_placeholder = col1.empty()
motorbike_placeholder = col2.empty()
car_placeholder = col3.empty()
total_vehicles_placeholder = col4.empty()

# Function to update metrics in the placeholders
def update_metrics():
    truck_value = fetch_truck_value()
    motorbike_value = fetch_motorbike_value()
    car_value = fetch_car_value()
    total_vehicles_value = fetch_total_vehicles_value()

    # Use markdown with Font Awesome icons
    truck_placeholder.metric(label=f"🚚 Truck", value=f"{truck_value} SAR")
    motorbike_placeholder.metric(label=f"🏍️ Motorbike", value=f"{motorbike_value} SAR")
    car_placeholder.metric(label=f"🚗 Car", value=f"{car_value} SAR")
    total_vehicles_placeholder.metric(label=f"🚘 Total Vehicles", value=f"{total_vehicles_value}")

# Display the metrics and update them every second
update_metrics()

# Only update the metrics every 1 second (1000 milliseconds)
if time.time() - st.session_state.last_update_time > 1:
    update_metrics()
    st.session_state.last_update_time = time.time()


# Initialize session state variables for managing map points
if "start_point" not in st.session_state:
    st.session_state["start_point"] = None
if "end_point" not in st.session_state:
    st.session_state["end_point"] = None
if "reset_map" not in st.session_state:
    st.session_state["reset_map"] = False


def reset_map():
    st.session_state["start_point"] = None
    st.session_state["end_point"] = None
    st.session_state["map_reset"] = True
    
# Set the Google Maps API Key (Replace 'YOUR_GOOGLE_MAPS_API_KEY' with your actual key)
GOOGLE_MAPS_API_KEY = 'AIzaSyBvsVrsscV50q6bVV7ofEm2tzCz08F1k1A'
map_html = f"""
<!DOCTYPE html>
<html>
  <head>
    <script src="https://maps.googleapis.com/maps/api/js?key={GOOGLE_MAPS_API_KEY}&callback=initMap" async defer></script>
    <script type="text/javascript">
      let map, startMarker, endMarker, directionsService, directionsRenderer;
      let startPoint = {st.session_state["start_point"]};
      let endPoint = {st.session_state["end_point"]};

      function initMap() {{
        directionsService = new google.maps.DirectionsService();
        directionsRenderer = new google.maps.DirectionsRenderer();
        map = new google.maps.Map(document.getElementById('map'), {{
          center: new google.maps.LatLng(24.7136, 46.6753),  // Coordinates of Riyadh
          zoom: 12,
        }});
        directionsRenderer.setMap(map);

        map.addListener('click', function(event) {{
          handleMapClick(event.latLng);
        }});

        if (startPoint) {{
          startMarker = new google.maps.Marker({{
            position: new google.maps.LatLng(startPoint.lat, startPoint.lng),
            map: map,
            label: "A",
          }});
        }}

        if (endPoint) {{
          endMarker = new google.maps.Marker({{
            position: new google.maps.LatLng(endPoint.lat, endPoint.lng),
            map: map,
            label: "B",
          }});
        }}

        if (startPoint && endPoint) {{
          calculateRoute(startPoint, endPoint);
        }}
      }}

      function handleMapClick(location) {{
        if (!startMarker) {{
          startMarker = new google.maps.Marker({{
            position: location,
            map: map,
            label: "A",
          }});
          startPoint = {{lat: location.lat(), lng: location.lng()}};
          document.getElementById("startLatLng").value = JSON.stringify(startPoint);
        }} else if (!endMarker) {{
          endMarker = new google.maps.Marker({{
            position: location,
            map: map,
            label: "B",
          }});
          endPoint = {{lat: location.lat(), lng: location.lng()}};
          document.getElementById("endLatLng").value = JSON.stringify(endPoint);
        }}
        toggleGetResultButton();
      }}

      function toggleGetResultButton() {{
        const startLatLng = document.getElementById("startLatLng").value;
        const endLatLng = document.getElementById("endLatLng").value;
        if (startLatLng && endLatLng) {{
          document.getElementById("getResultBtn").disabled = false;
        }} else {{
          document.getElementById("getResultBtn").disabled = true;
        }}
      }}

      function calculateRoute(start, end) {{
        const request = {{
          origin: new google.maps.LatLng(start.lat, start.lng),
          destination: new google.maps.LatLng(end.lat, end.lng),
          travelMode: 'DRIVING'
        }};
        directionsService.route(request, function(result, status) {{
          if (status === 'OK') {{
            directionsRenderer.setDirections(result);
          }}
        }});
      }}

      function resetMap() {{
        if (startMarker) {{
          startMarker.setMap(null);
          startMarker = null;
        }}
        if (endMarker) {{
          endMarker.setMap(null);
          endMarker = null;
        }}
        directionsRenderer.set('directions', null);
        document.getElementById("startLatLng").value = "";
        document.getElementById("endLatLng").value = "";
        startPoint = null;
        endPoint = null;
        toggleGetResultButton();
      }}
    </script>
  </head>
  <body>
    <div id="map" style="height: 500px; width: 100%;"></div>
    <input type="hidden" id="startLatLng" name="startLatLng">
    <input type="hidden" id="endLatLng" name="endLatLng">
  </body>
</html>
"""
# Embed the map in Streamlit
st.components.v1.html(map_html, height=500)

# Create two buttons for "Get Result" and "Reset"
col1, col2 = st.columns(2)

with col1:
    get_result_button = st.button("Get Result", key="getResultBtn", disabled=True)
    if get_result_button:
        # Get start and end points from the hidden input fields
        start_point = st.text_input("startLatLng")
        end_point = st.text_input("endLatLng")
        if start_point and end_point:
            st.session_state["start_point"] = eval(start_point)
            st.session_state["end_point"] = eval(end_point)
            st.session_state["reset_map"] = False  # Reset the map state to False after getting results

with col2:
    reset_button = st.button("Reset")
    if reset_button:
        st.session_state["start_point"] = None
        st.session_state["end_point"] = None
        st.session_state["reset_map"] = True  # Set reset map state to True

# Re-run the map if reset is triggered
if st.session_state["reset_map"]:
    st.experimental_rerun()

