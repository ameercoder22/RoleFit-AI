from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import fitz, io, re, os, json, urllib.request, random

load_dotenv()
app = FastAPI(title='ResumeIQ / RoleSync AI API', version='2.0.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

KNOWN=['python','java','c++','javascript','typescript','react','node.js','fastapi','django','flask','sql','postgresql','mysql','mongodb','aws','azure','gcp','git','github','docker','kubernetes','ci/cd','rest api','graphql','microservices','machine learning','tensorflow','pytorch','pandas','numpy','html','css','linux','redis','kafka','terraform','testing','agile','observability','system design','data structures','algorithms','communication','problem solving','llm','generative ai','openai','gemini','spark','hadoop']
STOP=set('the and for with that this from your you are our have has will using into their they about role job work years experience skills strong looking build building developer software engineer preferred requirements responsibility responsibilities candidate ideal required qualification qualifications'.split())
ALIASES={'restful':'rest api','rest':'rest api','continuous integration':'ci/cd','continuous deployment':'ci/cd','amazon web services':'aws','mongodb database':'mongodb','node':'node.js'}

def norm(s): return re.sub(r'\s+',' ',re.sub(r'[^a-z0-9+#.\-/ ]',' ',(s or '').lower())).strip()
def contains_skill(n,k):
    kk=k.replace('node.js','node')
    return kk in n
def skills(s):
    n=norm(s); found=[]
    for k in KNOWN:
        if contains_skill(n,k) and k not in found: found.append(k)
    return found
def words(s):
    return [ALIASES.get(w,w) for w in norm(s).split() if len(w)>3 and w not in STOP]

def semantic_similarity(a,b):
    try:
        from sentence_transformers import SentenceTransformer
        model=semantic_similarity.model if hasattr(semantic_similarity,'model') else None
        if model is None:
            model=SentenceTransformer(os.getenv('EMBEDDING_MODEL','all-MiniLM-L6-v2'))
            semantic_similarity.model=model
        v=model.encode([a,b],normalize_embeddings=True)
        return round(max(0,min(100,float(v[0] @ v[1])*100)))
    except Exception:
        A=set(words(a)); B=set(words(b)); return round(100*(2*len(A&B)/max(1,len(A)+len(B))))

def extract_section(text,name):
    lines=text.splitlines(); out=[]; active=False
    headers={'summary','skills','experience','education','projects','certifications','work experience','professional experience','achievements'}
    for line in lines:
        x=line.strip(); low=x.lower().rstrip(':')
        if low==name or (low in headers and name in low): active=True; continue
        if active and low in headers and low!=name: break
        if active and x: out.append(x)
    return out

def parse_resume(text):
    lines=[x.strip() for x in text.splitlines() if x.strip()]
    email=(re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+',text) or [''])[0]
    phone=(re.findall(r'(?:\+?\d[\d\s().-]{8,}\d)',text) or [''])[0]
    return {'personal':{'name':lines[0] if lines else 'Candidate','email':email,'phone':phone,'location':next((x for x in lines if re.search(r'Hyderabad|Bangalore|Bengaluru|Delhi|Mumbai|Pune|Kurnool|India',x,re.I)),''),'linkedin':next((x for x in re.findall(r'(?:https?://)?(?:www\.)?linkedin\.com/[^\s|]+',text,re.I)),''),'github':next((x for x in re.findall(r'(?:https?://)?(?:www\.)?github\.com/[^\s|]+',text,re.I)), '')},'skills':skills(text),'education':extract_section(text,'education'),'experience':extract_section(text,'experience'),'projects':extract_section(text,'projects'),'certifications':extract_section(text,'certifications'),'summary':' '.join(extract_section(text,'summary'))}

class AnalyzeRequest(BaseModel):
    resume_text:str
    job_description:str
class OptimizeRequest(AnalyzeRequest):
    selected_recommendations: List[str]=[]
class GenerateRequest(BaseModel):
    resume_text:str
    template:str='minimal'
    filename:str='Resume'
class InterviewStartRequest(BaseModel):
    resume_text:str
    job_description:str
class InterviewEvaluateRequest(BaseModel):
    question:str
    answer:str
    resume_text:str
    job_description:str
    round_name:str='Technical'


def analyze(req:AnalyzeRequest):
    r=parse_resume(req.resume_text); js=skills(req.job_description); rs=set(r['skills']); matched=[x for x in js if x in rs]; missing=[x for x in js if x not in rs]
    kw=list(dict.fromkeys(words(req.job_description)))[:60]; rn=norm(req.resume_text); covered=[k for k in kw if k in rn]
    coverage=round(len(covered)/max(1,len(kw))*100); sem=semantic_similarity(req.resume_text,req.job_description); skill_cov=round(len(matched)/max(1,len(js))*100)
    match=round(sem*.45+skill_cov*.35+coverage*.20)
    section_names=['experience','education','projects','skills']; section_count=sum(bool(r.get(x)) for x in section_names)
    contact=(5 if r['personal']['email'] else 0)+(5 if r['personal']['phone'] else 0)
    formatting=[]
    if re.search(r'\|.+\|',req.resume_text): formatting.append('Possible table or multi-column layout detected')
    if re.search(r'\[[^\]]+\]\([^\)]+\)',req.resume_text): formatting.append('Markdown links may not parse consistently in ATS')
    if len(req.resume_text)<700: formatting.append('Resume is short; add evidence, context and quantified impact where truthful')
    if len(req.resume_text)>6500: formatting.append('Resume is long; consider tightening low-value content')
    fmt=max(0,20-len(formatting)*5); kp=round(coverage*.25); sp=round(section_count/4*15); cp=min(10,round(len(req.resume_text)/350)); rp=round(match*.1)
    ats=min(100,kp+sp+fmt+contact+10+cp+rp)
    issues=formatting+[f'{x} is missing from the resume' for x in missing[:6]]+([] if r['personal']['email'] else ['Email address not detected'])+([] if r['personal']['phone'] else ['Phone number not detected'])
    recommendations=[]
    for x in missing[:6]: recommendations.append({'id':'skill-'+x.replace(' ','-').replace('/','-'),'title':f'Add {x}','detail':f'Include {x} only if you genuinely have experience with it. Mirror the job wording in a relevant skills/project/experience bullet.','type':'skill'})
    recommendations += [
      {'id':'quantify','title':'Quantify impact','detail':'Add real metrics to strong experience/project bullets where available.','type':'content'},
      {'id':'ats-format','title':'Use ATS-safe structure','detail':'Prefer standard headings, single-column text and consistent bullet formatting.','type':'format'},
      {'id':'mirror','title':'Mirror relevant JD language','detail':'Use the job description terminology for skills you already demonstrate.','type':'keyword'},
      {'id':'testing','title':'Strengthen evidence','detail':'Mention testing, reliability or deployment evidence when it is genuinely present.','type':'content'}]
    return {'resume':r,'job':{'skills':js,'keywords':kw},'match_score':match,'ats_score':ats,'keyword_coverage':coverage,'semantic_similarity':sem,'skill_coverage':skill_cov,'matched_skills':matched,'missing_skills':missing,'weak_keywords':[x for x in kw if x not in rn][:15],'ats_breakdown':{'Keyword Coverage':f'{kp}/25','Formatting':f'{fmt}/20','Sections':f'{sp}/15','Contact Information':f'{contact}/10','Section Structure':'10/10','Content Quality':f'{cp}/10','Job Relevance':f'{rp}/10'},'issues':issues,'recommendations':recommendations}

@app.get('/api/health')
def health(): return {'status':'ok','service':'RoleSync AI','version':'2.0.0'}

@app.post('/api/resume/parse')
async def parse(file:UploadFile=File(...)):
    data=await file.read(); name=file.filename or ''
    try:
        if name.lower().endswith('.pdf'):
            doc=fitz.open(stream=data,filetype='pdf'); text='\n'.join(p.get_text() for p in doc)
        elif name.lower().endswith('.docx'):
            from docx import Document
            doc=Document(io.BytesIO(data)); text='\n'.join(p.text for p in doc.paragraphs)
        else: text=data.decode('utf-8','ignore')
        return {'text':text,'structured':parse_resume(text)}
    except Exception as e: raise HTTPException(400,f'Could not parse resume: {e}')

@app.post('/api/analyze')
def analyze_endpoint(req:AnalyzeRequest):
    if not req.resume_text.strip() or not req.job_description.strip(): raise HTTPException(400,'Resume and job description are required')
    return analyze(req)

def call_gemini(prompt):
    key=os.getenv('GEMINI_API_KEY'); model=os.getenv('GEMINI_MODEL','gemini-2.5-flash')
    if not key: return None
    try:
        payload=json.dumps({'contents':[{'parts':[{'text':prompt}]}]}).encode()
        url=f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}'
        request=urllib.request.Request(url,data=payload,headers={'Content-Type':'application/json'},method='POST')
        with urllib.request.urlopen(request,timeout=30) as resp:
            data=json.loads(resp.read().decode()); return data['candidates'][0]['content']['parts'][0]['text'].strip()
    except Exception: return None

@app.post('/api/optimize')
def optimize(req:OptimizeRequest):
    base=analyze(req); selected=req.selected_recommendations or [x['title'] for x in base['recommendations'][:4]]
    prompt=f'''Rewrite this resume for the target job. FACTUAL INTEGRITY IS MANDATORY: never invent skills, employers, dates, metrics, certifications, projects or achievements. Only improve wording and structure using evidence already present. Apply these selected recommendations when truthful: {json.dumps(selected)}. Return only the complete revised resume.\n\nTARGET JOB:\n{req.job_description}\n\nRESUME:\n{req.resume_text}'''
    improved=call_gemini(prompt)
    if not improved:
        # Safe fallback: reorganize only; never claim missing skills were gained.
        improved=req.resume_text.strip()
        if selected:
            improved += '\n\nOPTIMIZATION NOTES\n' + '\n'.join('• '+x for x in selected)
    after=analyze(AnalyzeRequest(resume_text=improved,job_description=req.job_description))
    return {'optimized_text':improved,'analysis':after,'selected_recommendations':selected,'ai_used':bool(os.getenv('GEMINI_API_KEY'))}

@app.post('/api/resume/generate')
def generate_resume(req:GenerateRequest):
    from docx import Document
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.section import WD_SECTION
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    doc=Document(); sec=doc.sections[0]; sec.top_margin=Inches(.5); sec.bottom_margin=Inches(.5); sec.left_margin=Inches(.62); sec.right_margin=Inches(.62)
    lines=[x.strip() for x in req.resume_text.splitlines() if x.strip()]; name=lines[0] if lines else 'Candidate'
    headings={'SUMMARY','SKILLS','EXPERIENCE','EDUCATION','PROJECTS','CERTIFICATIONS','ACHIEVEMENTS','OPTIMIZATION NOTES'}
    template=req.template
    if template=='executive':
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.LEFT; r=p.add_run(name); r.bold=True; r.font.size=Pt(22)
        if len(lines)>1: p=doc.add_paragraph(lines[1]); p.runs[0].font.size=Pt(11)
        accent='1f2937'
    elif template=='modern':
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(name.upper()); r.bold=True; r.font.size=Pt(20)
        accent='2563eb'
    elif template=='tech':
        p=doc.add_paragraph(); r=p.add_run(name); r.bold=True; r.font.size=Pt(20); accent='0f766e'
    else:
        p=doc.add_paragraph(); p.alignment=WD_ALIGN_PARAGRAPH.CENTER; r=p.add_run(name); r.bold=True; r.font.size=Pt(19); accent='374151'
    for line in lines[1:]:
        u=line.upper().rstrip(':')
        if u in headings:
            p=doc.add_paragraph(); p.paragraph_format.space_before=Pt(8); rr=p.add_run(line); rr.bold=True; rr.font.size=Pt(10); rr.font.color.rgb=RGBColor.from_string(accent)
        else:
            p=doc.add_paragraph(line); p.paragraph_format.space_after=Pt(2); p.paragraph_format.line_spacing=1.0
            for rr in p.runs: rr.font.size=Pt(9.5)
    bio=io.BytesIO(); doc.save(bio); bio.seek(0)
    safe=re.sub(r'[^A-Za-z0-9_-]+','_',req.filename or 'Resume')
    return StreamingResponse(bio,media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',headers={'Content-Disposition':f'attachment; filename="{safe}_{template}.docx"'})

# ---------- Mock interview ----------

def fallback_questions(resume,jd):
    rs=skills(resume); js=skills(jd); target=list(dict.fromkeys(js+rs))
    q=[]
    for s in target[:5]:
        if s=='sql': q.append({'round':'Technical','difficulty':'Medium','question':'Write a SQL query to return the second-highest salary from an employees table. Explain your approach.'})
        elif s=='mongodb': q.append({'round':'Technical','difficulty':'Medium','question':'In MongoDB, how would you find all users from a given city and create an index to speed up that query?'})
        elif s=='python': q.append({'round':'Technical','difficulty':'Medium','question':'In Python, what is the difference between a list, tuple and set, and when would you choose each?'})
        elif s=='fastapi': q.append({'round':'Technical','difficulty':'Medium','question':'How would you design a FastAPI endpoint with validation, authentication and consistent error handling?'})
        elif s=='aws': q.append({'round':'Technical','difficulty':'Medium','question':'Describe how you would deploy a backend API on AWS and keep it reliable under increasing traffic.'})
        elif s=='docker': q.append({'round':'Technical','difficulty':'Easy','question':'Why use Docker for a backend service? Walk through a simple production deployment flow.'})
        elif s=='kubernetes': q.append({'round':'Technical','difficulty':'Medium','question':'What problem does Kubernetes solve, and what is the difference between a Deployment and a Service?'})
        elif s=='react': q.append({'round':'Technical','difficulty':'Medium','question':'How does React state differ from props, and how would you avoid unnecessary re-renders?'})
        elif s=='mongodb': pass
    q += [
      {'round':'Introduction','difficulty':'Easy','question':'Give me a 60-second introduction focused on the experience most relevant to this role.'},
      {'round':'Resume Deep Dive','difficulty':'Medium','question':'Pick the project on your resume most relevant to this job. Explain the architecture, your contribution, one challenge and the result.'},
      {'round':'Behavioral','difficulty':'Medium','question':'Tell me about a time you faced a difficult technical problem. How did you investigate it and what did you learn?'},
      {'round':'System Design','difficulty':'Hard','question':'Design a scalable backend service for this role. Cover API design, database choice, caching, observability and how you would handle failures.'},
      {'round':'Closing','difficulty':'Medium','question':'Why are you a strong fit for this role, and what would you want to learn in your first 90 days?'}]
    # 4 rounds, 8-10 questions total
    return q[:10]

@app.post('/api/interview/start')
def interview_start(req:InterviewStartRequest):
    prompt=f'''Create a realistic mock interview for a candidate based ONLY on their resume and the target job. Return JSON array of 10 questions across exactly these rounds: Introduction, Resume Deep Dive, Technical, Behavioral/System Design. Mix easy, medium and hard. Technical questions must use skills actually present in the resume or explicitly required by the job; include practical questions such as SQL queries when SQL is relevant. Do not ask about invented experience. Each item: round,difficulty,question.\nRESUME:\n{req.resume_text}\nJOB:\n{req.job_description}'''
    raw=call_gemini(prompt)
    questions=None
    if raw:
        try:
            txt=raw[raw.find('['):raw.rfind(']')+1]; questions=json.loads(txt)
        except Exception: questions=None
    if not questions: questions=fallback_questions(req.resume_text,req.job_description)
    return {'questions':questions[:10],'rounds':['Introduction','Resume Deep Dive','Technical','Behavioral/System Design']}

@app.post('/api/interview/evaluate')
def interview_evaluate(req:InterviewEvaluateRequest):
    prompt=f'''Evaluate this interview answer for the question. Score 0-100 using correctness, relevance, depth, clarity and role alignment. If technical, prioritize technical accuracy. Give concise feedback and one improvement. Do not judge personality. Return JSON with score,feedback,improvement.\nROUND:{req.round_name}\nQUESTION:{req.question}\nANSWER:{req.answer}\nRESUME:{req.resume_text}\nJOB:{req.job_description}'''
    raw=call_gemini(prompt); result=None
    if raw:
        try:
            txt=raw[raw.find('{'):raw.rfind('}')+1]; result=json.loads(txt)
        except Exception: result=None
    if not result:
        a=req.answer.strip(); q=req.question.lower(); score=45 if len(a)>40 else 20
        technical_terms=sum(1 for s in set(skills(req.resume_text)+skills(req.job_description)) if s in norm(a))
        score=min(95,score+technical_terms*8+min(20,len(a)//120)*5)
        if any(x in q for x in ['sql','query']): score=min(95,score+(10 if re.search(r'\bselect\b|\bjoin\b|\bwhere\b',a,re.I) else 0))
        result={'score':score,'feedback':'Your answer was assessed for relevance, specificity and technical evidence.','improvement':'Add a concrete example, explain your reasoning step-by-step, and connect the answer to the target role.'}
    return result
