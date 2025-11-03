# Dockerfile

# 1. Use an official Python runtime as a base image
FROM python:3.10-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Copy the requirements file into the container
COPY requirements.txt .

# 4. Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy your application code and the data file into the container
#    Note the quotes around "final 1.csv" to handle the space
COPY app.py .
COPY "final1.csv" .

# 6. Expose the port the app runs on (Dash default is 8050)
EXPOSE 8050

# 7. Set the command to run the application using Gunicorn
#    This is the production-ready way to run a Dash app
#    It looks for the 'server' variable inside the 'app.py' file
CMD ["gunicorn", "app:server", "-b", "0.0.0.0:8050"]
