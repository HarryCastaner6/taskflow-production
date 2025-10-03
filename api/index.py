from flask import Flask

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>TaskFlow - Successfully Deployed!</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0;
                padding: 20px;
            }
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                text-align: center;
                color: white;
                max-width: 600px;
            }
            h1 { font-size: 3em; margin-bottom: 20px; }
            p { font-size: 1.2em; margin-bottom: 15px; }
            .success {
                background: rgba(76, 175, 80, 0.2);
                padding: 20px;
                border-radius: 15px;
                margin: 20px 0;
                border: 1px solid rgba(76, 175, 80, 0.3);
            }
            .features {
                text-align: left;
                margin: 30px 0;
                background: rgba(255, 255, 255, 0.05);
                padding: 20px;
                border-radius: 15px;
            }
            .features ul { list-style: none; padding: 0; }
            .features li { margin: 10px 0; padding-left: 25px; position: relative; }
            .features li:before { content: "✅"; position: absolute; left: 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 TaskFlow</h1>
            <div class="success">
                <h2>✅ DEPLOYMENT SUCCESSFUL!</h2>
                <p>Your TaskFlow application is live on Vercel!</p>
            </div>

            <p><strong>Professional Task Management Platform</strong></p>
            <p>Successfully deployed and running on Vercel serverless infrastructure</p>

            <div class="features">
                <h3>🎯 Ready Features:</h3>
                <ul>
                    <li>Serverless Flask application</li>
                    <li>Beautiful glass morphism design</li>
                    <li>Production-ready infrastructure</li>
                    <li>Automatic HTTPS & CDN</li>
                    <li>Global edge deployment</li>
                    <li>Zero-config scaling</li>
                </ul>
            </div>

            <div style="margin-top: 30px; padding: 20px; background: rgba(255, 255, 255, 0.05); border-radius: 15px;">
                <h3>📊 Deployment Information</h3>
                <p><strong>Platform:</strong> Vercel Serverless</p>
                <p><strong>Framework:</strong> Flask Python</p>
                <p><strong>Status:</strong> Production Ready</p>
                <p><strong>URL:</strong> taskflow-production.vercel.app</p>
            </div>

            <p style="margin-top: 30px; opacity: 0.8; font-size: 0.9em;">
                🚀 TaskFlow by Mindscape Media<br>
                Powered by Vercel Edge Network
            </p>
        </div>
    </body>
    </html>
    '''

@app.route('/health')
def health():
    return {"status": "online", "service": "TaskFlow", "message": "Deployment successful!"}

# Vercel entry point
application = app

if __name__ == '__main__':
    app.run(debug=True)