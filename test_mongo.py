print("Program started")

from pymongo import MongoClient

print("Connecting to MongoDB...")

client = MongoClient("mongodb://localhost:27017/")

print("Connected")

db = client["mydatabase"]
collection = db["students"]

result = collection.insert_one({"name": "Praveen", "age": 20})

print("Inserted ID:", result.inserted_id)

for data in collection.find():
    print(data)

print("Program finished")