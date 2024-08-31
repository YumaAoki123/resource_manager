from __init__ import create_app  # Replace 'your_package_name' with your actual package name

if __name__ == "__main__":
    app = create_app()  # Create an instance of the app
    app.run(debug=True)  # Run the app