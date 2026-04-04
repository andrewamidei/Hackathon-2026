

# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your app's source code from your host to your image filesystem
COPY . .

# Streamlit (public) + FastAPI (internal)
EXPOSE 8501
EXPOSE 8000

RUN chmod +x start.sh

# Run both services via start.sh
CMD ["bash", "start.sh"]

