import requests
import os
import json
import base64

def deploy_to_vercel():
    # Vercel API configuration
    api_url = "https://api.vercel.com/v9/now/deployments"
    token = "WFXoJGa5qGtTELNXgYhkMaYA"  # Your Vercel token
    
    # Headers
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Files to deploy
    files = [
        "index.py",
        "vercel.json",
        "requirements.txt",
        "templates/attendance_form.html",
        "templates/admin/view_responses.html",
        "templates/admin/dashboard.html"
    ]
    
    # Prepare deployment data
    deployment_data = {
        "name": "scanmark",
        "files": [],
        "projectSettings": {
            "framework": "python",
            "buildCommand": "pip install -r requirements.txt",
            "outputDirectory": ".",
            "installCommand": "pip install -r requirements.txt",
            "devCommand": None
        },
        "target": "production",
        "env": {
            "FLASK_ENV": "production",
            "PYTHONPATH": "."
        }
    }
    
    # Add files
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Add file to deployment
            deployment_data["files"].append({
                "file": file_path,
                "data": content
            })
            print(f"✅ Added {file_path}")
            
        except Exception as e:
            print(f"❌ Error with {file_path}: {str(e)}")
            return False
    
    try:
        # Make deployment request
        print("\n🚀 Starting deployment...")
        response = requests.post(
            api_url,
            headers=headers,
            json=deployment_data
        )
        
        if response.status_code in [200, 201]:
            result = response.json()
            print("\n✨ Deployment started successfully!")
            print(f"Deployment URL: {result.get('url')}")
            print("\nYou can check the deployment status at:")
            print("https://vercel.com/rajatmaurya35/scanmark/deployments")
            print("\nOnce deployed, your app will be available at:")
            print("https://scan-mark.vercel.app")
            return True
        else:
            print(f"\n❌ Deployment failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"\n❌ Deployment error: {str(e)}")
        return False

if __name__ == "__main__":
    deploy_to_vercel()
