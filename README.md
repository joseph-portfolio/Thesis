# Microplastic Detection and Classification System

- A comprehensive system for detecting and classifying microplastics collected in surface water using computer vision and geolocation data.

## 🚀 Live Demo

https://github.com/user-attachments/assets/dd8f5d43-eaa8-4cf3-ada0-d447d15002bd

- https://thesis-g13y.onrender.com/

## 🌟 Features

- **Real-time Image Capture**: Captures high-resolution images of water samples
- **GPS Integration**: Logs precise location data for each sample
- **AI-Powered Detection & Classification**: Utilizes Faster R-CNN for both detecting microplastics and classifying their polymer types
- **Data Visualization**: Interactive dashboard for viewing detection results
- **Geospatial Mapping**: Visualizes microplastic distribution on an interactive map

## 📊 Data Flow

1. **Image Capture**: Raspberry Pi camera captures high-resolution images of water samples
2. **GPS Logging**: Concurrently records precise GPS coordinates for each sample
3. **AI Processing**: Image is processed by the Faster R-CNN model to detect microplastics and classify polymer types (PE, PP, PS)
4. **Data Storage**: Results, including detection data and GPS coordinates, are stored in AWS DynamoDB
5. **Media Storage**: Original and annotated images are saved to AWS S3
6. **Web Visualization**: A Flask-based web dashboard displays the data with interactive maps and charts

## 🤖 AI Model

The system uses a pre-trained Faster R-CNN model fine-tuned for microplastic detection. The model can identify:

- Microplastics
- Polymer types (PE PP, PS)

## 🌍 Deployment

### AWS SageMaker

[View SageMaker Documentation](https://sagemaker.readthedocs.io/en/stable/frameworks/pytorch/using_pytorch.html#bring-your-own-model)


