

# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache -r requirements.txt

# Copy the rest of your app's source code from your host to your image filesystem
COPY . .

# Make port 80 available to the world outside this container
EXPOSE 8501

# Define environment variable (optional)

# Run streamlit on start up
CMD ["streamlit", "run", "./src/main.py"]

