from django.db import models

# Create your models here.

class AccessTokendb(models.Model):
    firstName = models.CharField(max_length=25)
    email = models.EmailField(primary_key=True)
    token = models.TextField()
    refreshtoken = models.TextField(default="N/A")


class Test(models.Model) :
    integer = models.IntegerField()