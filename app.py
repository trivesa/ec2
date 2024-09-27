from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/trigger-script', methods=['POST'])
def trigger_script():
    # Trigger the execution of your Python script here
    # You can import and call the necessary functions from your existing script
    
    return jsonify({'message': 'Script execution triggered successfully'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
