# NIT Srinagar Billing System

## Setup the app

### Clone the repository

#### HTTPS

```bash
git clone https://github.com/SahibAhmad/BillingManagement.git
```

#### SSH

```bash

```

### Create a virtual environment

```bash
python3 -m venv venv
```

### Activate the virtual environment

#### Unix

```bash
source venv/bin/activate
```

#### Windows

```bash
venv\Scripts\activate.bat
```

### Install requirements

```bash
pip install -r requirements.txt
```

### Initialize the app

```bash
python3 manage.py makemigrations
python3 manage.py migrate
```
### Create Groups

```bash
python3 manage.py shell

>> from django.contrib.auth.models import Group
>> Group.objects.get_or_create(name='admin')
>> Group.objects.get_or_create(name='operator')
>> Group.objects.get_or_create(name='user')
>> exit()
```

## Deactivate the virtual environment

```bash
deactivate
```

## Run the app

### Activate the virtual environment

#### Unix

```bash
source venv/bin/activate
```

#### Windows

```bash
venv\Scripts\activate.bat
```

## Start the application

```bash
python3 manage.py runserver
```

## Deactivate the virtual environment

```bash
deactivate
```
