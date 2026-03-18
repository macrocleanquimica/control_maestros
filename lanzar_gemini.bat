@echo off  
python -c "from genai import Client; import sys; client = Client(api_key='AIzaSyDxLKsCBxeGxPbzP8bIjPPebafgAi0ccJ8'); response = client.models.generate_content(model='gemini-2.0-flash', contents=' '.join(sys.argv[1:])); print(response.text)" %* 
