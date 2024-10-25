from flask import Flask, request, jsonify, session
import sqlite3
from twilio.rest import Client
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)  # Set a secret key for session management

# Initialize Twilio API
account_sid = 'ACc8d76f521f32fcdcxxxxxxxxxxxxxxxx'  
auth_token = '2fd3582985b2ac18784exxxxxxxxxxxxx'    
whatsapp_number = 'whatsapp:+14155238886'  
client = Client(account_sid, auth_token)

# Initialize SQLite3 Database
def init_db():
    with sqlite3.connect('user_data.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                        (email TEXT, password TEXT)''')

# Insert user into the database
def insert_user(email, password):
    try:
        with sqlite3.connect('user_data.db') as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
            conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {str(e)}")

# Function to send WhatsApp message
def send_whatsapp_message(user_number, message):
    try:
        client.messages.create(
            body=message,
            from_=whatsapp_number,
            to=f'whatsapp:+{user_number}'
        )
    except Exception as e:
        print(f"Error sending WhatsApp message: {str(e)}")

# Dialogflow webhook route
@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    print(req)  # Debug: Print the incoming request data

    # Get the intent name to identify the interaction stage
    intent_name = req['queryResult']['intent']['displayName']
    
    # Handle the "Login Intent"
    if intent_name == 'Login Intent':
        # Set the output context for the next step
        return jsonify({
            'fulfillmentText': 'Please enter your email address.',
            'outputContexts': [
                {
                    'name': req['session'] + '/contexts/EmailIntent-followup',
                    'lifespanCount': 5
                }
            ]
        })

    # Handle the "Email Intent"
    elif intent_name == 'Email Intent':
        email = req['queryResult']['parameters'].get('email')
        print(f"Captured email: {email}")  # Debug: Check captured email
        if email:
            session['email'] = email  # Store email in session
            # Set output context for Password Intent
            return jsonify({
                'fulfillmentText': 'Now, please enter your password.',
                'outputContexts': [
                    {
                        'name': req['session'] + '/contexts/PasswordIntent-followup',
                        'lifespanCount': 5
                    }
                ]
            })
        else:
            return jsonify({'fulfillmentText': 'I didn’t get that. Can you please repeat your email?'})

    # Handle the "Password Intent"
    elif intent_name == 'Password Intent':
        password = req['queryResult']['parameters'].get('password')
        
        # Retrieve the stored email
        email = session.get('email')  # Get the email from session
        
        if email and password:
            # Save email and password to the SQLite3 database
            insert_user(email, password)
            
            # Retrieve the user's WhatsApp number from the parameters
            user_whatsapp_number = req['queryResult']['parameters'].get('user_phone_number')
            if user_whatsapp_number:
                send_whatsapp_message(user_whatsapp_number, 'Your account has been successfully registered!')
                return jsonify({'fulfillmentText': 'Thank you! Your account has been registered.'})
            else:
                return jsonify({'fulfillmentText': 'I could not retrieve your phone number. Please provide it.'})
            
        else:
            return jsonify({'fulfillmentText': 'I could not retrieve your email or password. Please start over.'})

    # If intent not recognized
    return jsonify({'fulfillmentText': 'Sorry, I did not understand that.'})

@app.route('/')
def index():
    return "Flask server is running!"

# Initialize the database
init_db()

if __name__ == '__main__':
    app.run(port=5000, debug=True)
