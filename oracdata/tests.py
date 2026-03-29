from django.test import TestCase
import pickle
with open('userData.pkl', 'rb') as f:
    data = pickle.load(f)

print(data)
# Create your tests here.
