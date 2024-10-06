# Sum (سم) - AI-Driven Traffic Management System
 
## Introduction 

**Sum** is an AI-driven system designed for real-time traffic monitoring and management. Utilizing advanced deep learning models, including computer vision and time series analysis, Sum accurately detects vehicle types and license plates. It dynamically adjusts congestion costs based on traffic conditions and time of day to reduce congestion, enhance road safety, and improve overall traffic efficiency.

## Features

- **Vehicle and License Plate Detection**: Sum uses YOLO for detecting vehicle types and OCR for reading license plates.
- **Dynamic Congestion Pricing**: The system implements congestion pricing for busy roads, encouraging the use of less congested routes.
- **Real-Time Traffic Monitoring**: Leveraging Google API, Sum detects busy roads and adjusts routing recommendations accordingly.
- **Dashboard Interface**: A user-friendly dashboard provides the fastest routes without incurring congestion fees.

## Methodology

### Data Collection

1. **Google API**: 
   - Utilized to gather real-time data on road conditions, traffic density, and busy routes. This API provides essential information that assists in making informed decisions regarding congestion pricing and optimizing route recommendations.

2. **YouTube Videos**: 
   - Employed for gathering insights and training data, including footage from static cameras to detect vehicles and license plates. Additionally, dashcam videos are used specifically for training the YOLO model in vehicle detection and license plate recognition. This combination enhances the model's accuracy and robustness by providing real-world examples of traffic conditions.

### Model Training

1. **YOLO (You Only Look Once)**:
   - A state-of-the-art object detection model is implemented to identify vehicle types and license plates in real-time. The model is trained using labeled datasets derived from the collected video footage.

2. **Optical Character Recognition (OCR)**:
   - Implemented using a transformer model to accurately read and interpret license plate information from the detected vehicles, ensuring reliable identification for traffic       management.
### Dynamic Congestion Pricing

1. **Cost Adjustment**:
   - The system identifies busy roads and applies congestion fees to discourage use during peak times, effectively reducing traffic in high-density areas.

2. **Route Optimization**:
   - By analyzing real-time data, the system recommends alternative routes with lower traffic density and no congestion fees, guiding drivers to less congested paths.

### Dashboard Interface

1. **User-Friendly Design**:
   - The dashboard provides an intuitive interface for users to access real-time traffic data, visualize road conditions, and receive route recommendations.

2. **Interactive Maps**:
   - Displays current traffic conditions and suggests the fastest routes without incurring congestion fees, enhancing user experience and traffic management efficiency.


## Installation







## Result



## Project Members

- **[Majid Almadani]**
  - Email: [AlmadaniMajidcs@gmail.com]   
  - GitHub: [MajidAlmadani](https://github.com/MajidAlmadani)   
  - LinkedIn: [majidalmadani](https://www.linkedin.com/in/majidalmadani/) 

- **[Abdulaziz Koja]**
  - Email: [Abdulazizkoja.1@gmail.com]     
  - GitHub: [Abdulazizkoja1](https://github.com/Abdulazizkoja1)  
  - LinkedIn: [abdulazizkoja](www.linkedin.com/in/abdulazizkoja) 

- **[Ziyad Qutub]**
  - Email: [ziad36311@gmail.com] 
  - GitHub: [ZiaydQutub](https://github.com/ZiyadQutub)    
  - LinkedIn: [ziyad-qutub](linkedin.com/in/ziyad-qutub/) 

- **[Ahmed Bashmmakh]**
  - Email: [aabx9x@gmail.com]   
  - GitHub: [a90h09](https://github.com/a90h09)  
  - LinkedIn: [ahmed-bashmmakh](https://www.linkedin.com/in/ahmed-bashmmakh/)
 
- **[Sarah Alkanhal]**
  - Email: [sarah.alkanhall@gmail.com] 
  - GitHub: [sarahmkk11](https://github.com/sarahmkk11)  
  - LinkedIn: [sarah-alkanhal-132083222](linkedin.com/in/sarah-alkanhal-132083222/) 
  
