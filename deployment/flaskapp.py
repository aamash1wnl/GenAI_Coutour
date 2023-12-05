from flask import Flask, render_template, request, redirect, url_for
import os
from class_model import ModelClassDep  # Replace with the actual function name
from flask import send_file  # Add this import

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['STATIC_FOLDER'] = 'static'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/result', methods=['POST'])
def result():
    image = request.files['image']
    prompts = request.form['prompts'].split(',')
    patterns = request.form['patterns'].split(',')

    # Save uploaded image
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image.filename)
    image.save(image_path)
    print(prompts, patterns, image_path)
    # Call your model function here
    result_image_path = ModelClassDep(image_path, prompts, patterns).model_execution()

    return send_file(result_image_path, mimetype='image/png')  # Send image file directly


if __name__ == '__main__':
    app.run(debug=True)
