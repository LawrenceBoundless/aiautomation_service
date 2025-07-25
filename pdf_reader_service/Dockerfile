# pdf_reader_service/Dockerfile

# 1. Use an official Python runtime as a parent image
FROM python:3.10-slim

# 2. Set the working directory in the container
WORKDIR /code

# 3. Copy the requirements file and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# 4. Copy the application code into the container
COPY ./app /code/app

# 5. Command to run the application using Uvicorn
#    We use 0.0.0.0 to make it accessible from outside the container.
#    The port is set to 8080, which is standard for Cloud Run.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]