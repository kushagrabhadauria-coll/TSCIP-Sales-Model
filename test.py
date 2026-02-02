# import vertexai
# from vertexai.generative_models import GenerativeModel

# vertexai.init(project="mec-transcript", location="us-central1")

# model = GenerativeModel("gemini-2.5-flash")
# print(model.generate_content("Say 'impersonation working'").text)


import vertexai
from vertexai.generative_models import GenerativeModel, Part

vertexai.init(project="mec-transcript", location="us-central1")

model = GenerativeModel("gemini-2.5-flash")

with open("test.mp3", "rb") as f:
    audio = Part.from_data(f.read(), mime_type="audio/mpeg")

resp = model.generate_content(["Transcribe this call", audio])
print(resp.text)
