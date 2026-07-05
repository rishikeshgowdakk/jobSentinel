def main():
    with open('src/api.py', 'r') as f:
        content = f.read()

    injection = """        structured_data = analyzer.extract_resume_parameters(text)
        
        # Auto-tune scraper keywords
        current_role = structured_data.get("current_role", "")
        top_skills = structured_data.get("skills", [])[:3]
        new_kw = []
        if current_role and current_role not in ["Candidate Profile", "Software Engineer"]:
            new_kw.append(current_role)
        new_kw.extend(top_skills)
        if new_kw:
            db.set_setting(user_id, "keywords", ", ".join(new_kw))
            logger.info(f"Auto-tuned scraper keywords to: {', '.join(new_kw)}")"""

    # We need to replace exactly the line: `        structured_data = analyzer.extract_resume_parameters(text)`
    # but we must only replace it where it makes sense. Since it appears in upload_resume and paste_resume.
    content = content.replace('        structured_data = analyzer.extract_resume_parameters(text)', injection)

    with open('src/api.py', 'w') as f:
        f.write(content)
        
    print("api.py updated successfully.")

if __name__ == '__main__':
    main()
