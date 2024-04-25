import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
import re


BASE_URL = "http://collegecatalog.uchicago.edu"

def request_with_delay(url):
    """Request a URL with a 3-second delay between requests, logging each request."""
    print(f"Requesting {url}")
    time.sleep(3)
    response = requests.get(url)
    if response.status_code == 200:
        print(f"Received response for {url}")
        return response
    else:
        print(f"Failed to fetch {url} with status code {response.status_code}")
        return None




def clean_text(text):
    """Clean text to remove unwanted characters and fix encoding issues."""
    return text.replace('Â', '').strip()

def parse_course_details(course_html):
    """Extract details from a course HTML snippet."""
    try:
        course_block_title = clean_text(course_html.find('p', class_='courseblocktitle').get_text())
        
        # Check if the title includes a sequence and skip it
        if '-' in course_block_title:  
            return None

        # Remove ". 100 Units." if it appears in the course title
        course_block_title = course_block_title.replace('. 100 Units.', '')
        
        # Split to get the course ID and the course name
        course_id, course_name = course_block_title.split('.', 1)
        course_id = course_id.strip()
        course_name = course_name.strip()

        # Extract description
        description = clean_text(course_html.find('p', class_='courseblockdesc').get_text())

        # Initialize defaults
        terms_offered = "Not specified"
        equivalent_courses = "None"
        instructors = "N/A"
        prerequisites = "None"

        # Handling details text
        detail_info = clean_text(course_html.find('p', class_='courseblockdetail').get_text())
        
        # Use regular expressions to extract various details
        terms_offered_match = re.search(r'Terms Offered: (.*?)(?:<br>|Equivalent Course\(s\)|Prerequisite\(s\)|Note\(s\)|$)', detail_info, re.DOTALL)
        if terms_offered_match:
            terms_offered = terms_offered_match.group(1).strip()

        equivalents_match = re.search(r'Equivalent Course\(s\): (.+?)(?:$|Instructor\(s\)|Prerequisite\(s\))', detail_info)
        if equivalents_match:
            equivalent_courses = equivalents_match.group(1).strip()

        instructors_match = re.search(r'Instructor\(s\): (.+?)(?:$|Terms Offered:|Prerequisite\(s\))', detail_info)
        if instructors_match:
            instructors = instructors_match.group(1).strip()

        prerequisites_match = re.search(r'Prerequisite\(s\): (.+?)(?:$|Terms Offered:|Equivalent Course\(s\))', detail_info)
        if prerequisites_match:
            prerequisites = prerequisites_match.group(1).strip()

        return {
            'Course ID': course_id,
            'Course Name': course_name,
            'Description': description,
            'Terms Offered': terms_offered,
            'Equivalent Courses': equivalent_courses,
            'Instructors': instructors,
            'Prerequisites': prerequisites
        }
    except AttributeError:
        return None  # Safely handle unexpected HTML structures


    
    

def crawl_department(department_url):
    """Crawl a department page for course details."""
    response = request_with_delay(department_url)
    if response:
        soup = BeautifulSoup(response.text, 'html.parser')
        course_blocks = soup.find_all('div', class_='courseblock')
        courses = [parse_course_details(block) for block in course_blocks if parse_course_details(block)]
        return courses
    else:
        return []

def main():
    start_url = BASE_URL + "/thecollege/programsofstudy/"
    response = request_with_delay(start_url)
    
    if response:
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.select('ul.nav.leveltwo li a')
        
        all_courses = []
        department_data = []

        for link in links:
            department_name = link.get_text(strip=True)
            department_url = BASE_URL + link['href']
            department_courses = crawl_department(department_url)
            all_courses.extend(department_courses)
            print(f"Processed {len(department_courses)} courses from {department_name}")

            # Add department data to the list
            department_data.append({
                'Department': department_name,
                'Number of Courses': len(department_courses)
            })
        
        # Filter out None before creating DataFrame for catalog
        all_courses = [course for course in all_courses if course]
        catalog_df = pd.DataFrame(all_courses)
        catalog_file_path = os.path.join(os.getcwd(), 'catalog.csv')
        catalog_df.to_csv(catalog_file_path, index=False)
        print(f"Completed scraping, catalog saved at {catalog_file_path}")

        # Create and save department DataFrame
        department_df = pd.DataFrame(department_data)
        department_file_path = os.path.join(os.getcwd(), 'department.csv')
        department_df.to_csv(department_file_path, index=False)
        print(f"Department data saved at {department_file_path}")

if __name__ == "__main__":
    main()