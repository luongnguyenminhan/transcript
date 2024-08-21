from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from util import MeetingAnalyzer
import os, uvicorn

app = FastAPI()
agent = MeetingAnalyzer()

@app.get("/api/")
async def read_root():
    return {"message": "Hello, World"}

@app.post("/api/uploadfile/")
async def upload_file(file: UploadFile = File(...)):
    try:
        await delete_file()  # Ensure previous file is deleted
        content = await file.read()
        transcript = content.decode("utf-8")
        
        await agent.complete(transcript)  # Process the transcript with the agent
        
        return {
            "response": "File uploaded successfully",
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@app.get("/api/downloadfile/")
async def download_file():
    file_location = agent.get_output_path()
    
    if not os.path.exists(file_location):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_location,
        media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        filename='Meeting_note.docx'
    )

@app.delete("/api/deletefile/")
async def delete_file():
    file_location = agent.get_output_path()

    if not os.path.exists(file_location):
        return {"response": "File not found"}

    try:
        os.remove(file_location)
        return {
            "response": "File deleted successfully",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"File deletion failed: {str(e)}")

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)

