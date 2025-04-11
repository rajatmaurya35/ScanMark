import requests
import os
import json
import base64

def deploy_to_vercel():
    # Vercel API configuration
    api_url = "https://api.vercel.com/v13/deployments"
    token = "7kMdZNGkiYHXCMGnSPVEwzOgbPQJrx3VLyX2"  # Updated token
    
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
        "gitSource": {
            "type": "github",
            "repo": "rajatmaurya35/ScanMark",
            "ref": "main"
        },
        "framework": "python",
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
                "data": base64.b64encode(content.encode()).decode()
            })
            print(f"✅ Added {file_path}")
            
        except Exception as e:
            print(f"❌ Error with {file_path}: {str(e)}")
            continue
    
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
            print("\nYour app will be available at:")
            print("https://scan-mark.vercel.app")
            return True
        else:
            print(f"\n❌ Deployment failed: {response.text}")
            print("\nPlease deploy manually through Vercel dashboard:")
            print("1. Go to https://vercel.com/rajatmaurya35/scanmark")
            print("2. Click 'Import Project'")
            print("3. Connect to your GitHub repository")
            print("4. Select:")
            print("   - Framework Preset: Python")
            print("   - Build Command: pip install -r requirements.txt")
            print("   - Install Command: pip install -r requirements.txt")
            print("   - Output Directory: .")
            return False
            
    except Exception as e:
        print(f"\n❌ Deployment error: {str(e)}")
        print("\nPlease deploy manually through Vercel dashboard:")
        print("1. Go to https://vercel.com/rajatmaurya35/scanmark")
        print("2. Click 'Import Project'")
        print("3. Connect to your GitHub repository")
        print("4. Select:")
        print("   - Framework Preset: Python")
        print("   - Build Command: pip install -r requirements.txt")
        print("   - Install Command: pip install -r requirements.txt")
        print("   - Output Directory: .")
        return False

if __name__ == "__main__":
    deploy_to_vercel()
