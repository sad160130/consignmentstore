from app import app

if __name__ == '__main__':
    print("Starting server at http://localhost:8080")
    app.run(host='0.0.0.0', port=8080, debug=True)