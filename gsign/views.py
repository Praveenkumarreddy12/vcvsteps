from django.shortcuts import render, HttpResponse, redirect
from django.core.mail import send_mail
from django.core.mail import EmailMessage
from .models import Test, AccessTokendb as ATT
from django.contrib import messages
from datetime import datetime, timedelta

from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

import json

import requests
import time
import csv
import os
import pytz
import jwt
import http.client
import time as timer
# Create your views here.



def gnerateaccess(refresh_token):
        url = 'https://oauth2.googleapis.com/token'

        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': '368680050758-r709ccn0u05mg04kna7g1rf0i789rir8.apps.googleusercontent.com',
            'client_secret': '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'
        }
        headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
        }

        response = requests.post(url, data=payload, headers=headers)

        # Output the response
        print('++'*10)
        print(refresh_token)
        print("++"*10)
        res = response.json()
        print(res.get("access_token"))
        return res.get("access_token")
# generate csv file function.
def generatecsv(ACCESS_TOKEN,file_mail):
    # Google Fit endpoint for aggregated data (steps, distance, etc.)
    URL = "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate"


    tz = pytz.timezone("Asia/Kolkata")
    end_date = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=30)


    end_time_millis = int(end_date.timestamp()* 1000)
    start_time_millis = int(start_date.timestamp()* 1000)

    # Request payload for step count data
    payload = {
        "aggregateBy": [{
            "dataTypeName": "com.google.step_count.delta",
            # "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps"
        }
        ],
        "bucketByTime": { "durationMillis": 86400000 },  # daily bucket
        "startTimeMillis": start_time_millis,
        "endTimeMillis": end_time_millis
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    response = requests.post(URL, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        rows = []
        print("Google Fit Step Count (Last 24h):")
        for bucket in data["bucket"]:
            start = int(bucket["startTimeMillis"])
            end = int(bucket["endTimeMillis"])
            date_str = time.strftime('%Y-%m-%d', time.localtime(start / 1000))
            for dataset in bucket["dataset"]:
                for point in dataset["point"]:
                    steps = point["value"][0]["intVal"]
                    rows.append([date_str, steps])
                    print(f"Steps: {steps}")
        
        file_mail = file_mail
        file_name = str(file_mail).split('@')[0]
        filename = file_name+".csv"
        file_path = os.path.join(settings.MEDIA_ROOT, filename)

        with open(file_path, mode="w+", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Date", "Steps"])  # Header
            writer.writerows(rows)

        print("✅ Step data saved to google_fit_steps.csv")
        full_path = os.path.abspath(filename)
        print(f"✅ Step data saved to: {full_path}")
        return True
    # elif response.status_code == 401  and refresh_token != None:
    #     url = 'https://oauth2.googleapis.com/token'

    #     payload = {
    #         'grant_type': 'refresh_token',
    #         'refresh_token': refresh_token,
    #         'client_id': '368680050758-r709ccn0u05mg04kna7g1rf0i789rir8.apps.googleusercontent.com',
    #         'client_secret': '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'
    #     }
    #     headers = {
    #     'Content-Type': 'application/x-www-form-urlencoded'
    #     }

    #     response = requests.post(url, data=payload, headers=headers)

    #     # Output the response
    #     print('--'*10)
    #     print(refresh_token)
    #     print("--"*10)
    #     res = response.json()
    #     print(res.get("access_token"))
    #     return generatecsv(res.get("access_token"),refresh_token,file_mail)

        


    else:
        print(f"Error: {response.status_code}")
        return False


def send_mail_csv(mail,file_mail):
    subject = 'CSV Report Attached'
    body = 'Please find the attached CSV file.'
    from_email = 'praveenkumarreddy1202@example.com'
    to_email = mail

    email = EmailMessage(subject, body, from_email, to_email)

    
    file_mail = file_mail
    file_name = str(file_mail).split('@')[0]

    csv_path = os.path.join(settings.MEDIA_ROOT, file_name + ".csv")


    # Attach the CSV file
    with open(csv_path, 'rb') as f:
        email.attach(file_name, f.read(), 'text/csv')

    # Send the email
    email.send()

def signin(request):
    return render(request,'signin.html')
    
@csrf_exempt
def exchange_code(request):
    code = request.GET.get('code')
    print("Authorization Code:", code)

    if not code:
        return HttpResponseBadRequest("Missing authorization code")

    # Exchange code for token
    token_res = requests.post('https://oauth2.googleapis.com/token', data={
        'code': code,
        'client_id': '368680050758-r709ccn0u05mg04kna7g1rf0i789rir8.apps.googleusercontent.com',
        'client_secret': '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',
        'redirect_uri': 'https://cd62-223-185-132-97.ngrok-free.app/exchange-code',
        'grant_type': 'authorization_code'
    })

    token_data = token_res.json()
    print("Token Response:", token_data)

    id_token = token_data.get('id_token')

    if not id_token:
        return HttpResponseBadRequest("No ID token found in token response")

    try:
        # Decode without verifying signature (for dev)
        user_info = jwt.decode(id_token, options={"verify_signature": False})
        email = user_info.get('email')
        first_name = user_info.get('given_name')

        if not email:
            return HttpResponseBadRequest("Email not found in ID token")

        # Save or update user info
        ATT.objects.update_or_create(
            email=email,
            defaults={
                'firstName': first_name,
                'token': token_data.get('access_token'),
                'refreshtoken': token_data.get('refresh_token')
            }
        )

        # ✅ Redirect like /done?email=email@example.com
        return redirect(f'/google?email={email}')

    except Exception as e:
        return HttpResponseBadRequest(f"Error decoding ID token: {str(e)}")


    # return JsonResponse({
    #     'access_token': token_data.get('access_token'),
    #     'refresh_token': token_data.get('refresh_token'),
    #     'email': email,
    #     'first_name': first_name
    # })

def done(request):
    # try :
        # token = request.GET.get('accessToken')
        # mail = []
        # mail.append("siddesh.bijavara@gmail.com")
        # mail.append(request.GET.get('email'))
        # mail = request.GET.get('email')
    #     token = ATT.objects.filter(email=email)

    #     generatecsv(token)
    #     obj = ATT.objects.update_or_create(
    #     email=request.GET.get('email'),
    # defaults={
    #     'firstName': 'testuser',
    #     'token': token
    # }
    #     )
    #     # obj.save()
        
    #     # send_mail_csv(mail)
    # except Exception as e :
    #     print("Error :- \n\n ",e)
    #     messages.error(request,f"An Error occured : - email = {mail} {str(e)}")
            
    #     return redirect('home')
    
    print("Done")
    return render(request,'done.html')

def generateCsv_db():
    records = ATT.objects.all().values('token', 'refreshtoken', 'email')
    # tst = Test.objects.values_list('token',flat=True)
    mails = []
    for record in records:
        mail =(record['email'])
        mails.append(mail)
        print("Email :- ",mail)
        print("Generating CSV")
        token = gnerateaccess(record['refreshtoken'])
        print("token :- ",token)
        generate = generatecsv(token,record['email'])
        print("generated csv file.")

        if generate :
            print("email is sended...")
            send_mail_csv(["jobcracking907@gmail.com","siddesh.bijavara@gmail.com"],mail)
            print("email sended.")
            timer.sleep(10)
        
    return mails

def generateCsvtoAll(request):
    tk = generateCsv_db()
    mails = "\n".join(tk)
   
    return HttpResponse(mails)
    


