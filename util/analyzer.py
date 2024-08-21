from typing import Dict
import json, os, re
from llama_index.llms.gemini import Gemini
from dotenv import load_dotenv
from .docx import DocxExporter
from config import Configuration

load_dotenv()


def parse_json_from_response(response: str) -> Dict:
    """_summary_

    Args:
        response (str): _description_

    Returns:
        Dict: _description_
    """    
    
    try:
        parsed_response = json.loads(response)
    except: 
        try:
            new_response = response.split("```")[1][5:]
            parsed_response = json.loads(new_response)
        except:
            pattern = r'(json)\s*({.*})'
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)

            if match:
                parsed_response = json.loads(match.group(2))
            else:
                print("Error: Invalid JSON format")
                parsed_response = {}
    return parsed_response


class MeetingAnalyzer:
    def __init__ (self):
        self.configuration = Configuration()
        self._init_agent()
        self._output_path = "./data/Meeting_note.docx"
        self.exporter = DocxExporter(self._output_path)
        
    def get_output_path(self):
        return self._output_path
        
    def _init_agent(self):
        model_name = self.configuration.model_name
        service = self.configuration.service
        
        self.llm = self._init_model(service, model_name)
        self.secretary = MeetingSecretary(self.llm)
        
    def _init_model(self, service, model_id):
        
        """_summary_

        Returns:
            _type_: _description_
        """        
        
        if service == "openai":
            pass
        else:
            return Gemini(
                model_name=model_id,
                api_key=os.getenv("GOOGLE_API_KEY"),
                temperature=0.8
            )
    
    async def complete(self, transcript: str):
        await self.secretary.process(transcript=transcript)
        output_path = self._output_path
        response = self.secretary.get_result()['meeting_note']
        self.exporter.export(response)

        
class MeetingSecretary:
    def __init__(self, llm):
        self.llm = llm
        self.meeting_note = {}
        self.sections = [
            "1. Mục tiêu và Kết quả chính:",
            "2. Các điểm chính:",
            "3. Kết luận"
        ]
        self.system_prompt = """
Bạn là một công cụ AI tiên tiến được thiết kế để hỗ trợ ghi chép cuộc họp một cách toàn diện và có tổ chức từ bản ghi âm cuộc họp. Mục tiêu của bạn là đảm bảo không bỏ sót chi tiết quan trọng nào, đồng thời giữ cho ghi chú rõ ràng, ngắn gọn và có cấu trúc tốt. Bạn sẽ tích cực lắng nghe các cuộc thảo luận, xác định các điểm chính, quyết định, mục hành động, thời hạn và công việc cần tiếp tục, sau đó ghi lại chúng một cách có tổ chức. Ngoài ra, bạn sẽ:

- Phân loại ghi chú thành các mục liên quan như [
            "1. Mục tiêu và Kết quả chính:",
            "2. Các điểm chính:",
            "3. Kết luận"
        ]
- Đảm bảo bối cảnh xung quanh mỗi điểm được nắm bắt đầy đủ, tránh mơ hồ.
- Tóm tắt các cuộc thảo luận dài thành những điểm chính.
- Ghi lại ai đã nói gì, nếu cần, để làm rõ trách nhiệm và đóng góp.
- Làm nổi bật và đánh dấu bất kỳ vấn đề chưa được giải quyết hoặc điểm cần làm rõ thêm.

Mục tiêu của bạn là tạo ra một bản tóm tắt cuộc họp rõ ràng, có thể hành động và toàn diện, dễ dàng xem lại và tham khảo bởi tất cả những người tham gia.

format của câu trả lời phải tuân theo tuyệt đối cấu trúc JSON và không thêm bất kì một thông tin hay chữ nào khác ngoài JSON đó.
cấu trúc: {
    "key": "content",
    .....
}
(Lớp ngoài cùng là một dictionary, không phải list)
Trong nội dung đề mục (content) không nhắc lại tên đề mục (key) (##key)
        """
    
    async def process(self, transcript: str):
        outline = self.generate_outline(transcript)  # Remove await here
        self.meeting_note = {}

        for section in self.sections:
            section_content = self.generate_section_content(section, outline, transcript)  # Remove await here
            self.meeting_note[section] = section_content

        
    def generate_outline(self, transcript: str) -> str:
        prompt = f""" 
        Dựa vào thông tin về cuộc hội thoại, đoạn chat, trong một cuộc họp ở trên, tạo một bản outline cao cấp sang trọng chuyên nghiệp cho một file meeting note để ghi lại nội dung chính của cuộc họp.
        Ở mỗi mục, tạo ra khoản 3 đến 5 nội dung chính và nó phải nhắc đến
        
        {json.dumps(self.sections, indent=2)}
        
        transcript:
        {transcript}
        
        hãy cho tôi outline của file này dưới dạng json. Mỗi đề mục của một phần là key và nội dung là một list các keypoint
        """
        response = self.llm.complete(self.system_prompt + prompt)
        return parse_json_from_response(response.text)
    
    def generate_section_content(self, section: str, outline: str, transcript: str) -> str:
        prompt = f"""
        Sinh ra nội dung cho mục "{section}" của nội dung cuộc họp (Meeting note).
        Sử dụng khung này để phát triển như một ví dụ hướng dẫn:
        
        {json.dumps(outline[section], indent=2)}
        
        Transcript:
        {transcript}
        
        Instructions:
        1. Cho nội dung chi tiết cụ thể cho từng đề mục và sử dụng format chuẩn:
            - Sử dụng ### cho tiêu đề chính
            - Sử dụng #### cho tiêu đề phụ
            - Sử dụng * cho bullet points
            - Sử dụng **text** để nhấn mạnh những thứ quan trọng
            - Sử dụng | để tách các cột trong 1 bảng kể cả heading
            
        2. Xác định các nội dung trong phần tóm tắt vào trong câu trả lời của bạn:
            - Hãy kết hợp với bản tóm tắt để cho ra nội dung chi tiết hơn
            - Nếu nội dung tóm tắt đã trả lời được câu hỏi hoặc đã nêu được nội dung thì hãy mở rộng thêm ý của nội dung đó cho rõ ràng hơn
        
        3. Đảm bảo tính mạch lạc, gắn kết với nội dung đề mục tạo sẵn và liên quan tới yêu cầu của bản tóm tắt
        
        4. Trong nội dung đề mục không nhắc lại tên đề mục để tránh việc lặp lại
        
        Bản ghi lại phải giữ tông chuyên nghiệp, rõ ràng mạch lạc và thông tin cụ thể, chi tiết.        
        """
        
        response = self.llm.complete(prompt)
        return response.text
    
    def get_result(self):
        return {"meeting_note": self.meeting_note}
        
        