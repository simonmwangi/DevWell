# DevWell: Developer Wellness Platform

## 🌟 Project Overview
DevWell is an intelligent developer wellness platform that combines AI/ML with software development analytics to promote sustainable development practices and developer well-being. The platform analyzes development patterns through their Git repositories, provides wellness recommendations, and helps developers maintain a healthy work-life balance while being productive.

## 🎯 Sustainable Development Goals (SDGs) Addressed

### 🎯 SDG 3: Good Health and Well-being
- **Mental Health Monitoring**: Tracks developer activity patterns to identify potential burnout risks
- **Wellness Recommendations**: Provides personalized suggestions for breaks, exercise, and work-life balance
- **Sentiment Analysis**: Analyzes commit messages and journal entries to monitor emotional well-being

### 🎯 SDG 8: Decent Work and Economic Growth
- **Productivity Insights**: Helps optimize work patterns for sustainable productivity
- **Work-Life Balance**: Encourages healthy work habits to prevent burnout
- **Skill Development**: Identifies areas for professional growth through code analysis

### 🎯 SDG 9: Industry, Innovation, and Infrastructure
- **Code Quality Analysis**: Promotes sustainable software development practices
- **Infrastructure Optimization**: Identifies areas for technical debt reduction
- **Innovation Tracking**: Monitors project progress and innovation metrics

## 🤖 AI/ML Technologies Used

### Core Machine Learning
- **Natural Language Processing (NLP)**:
  - TextBlob for sentiment analysis of commit messages and journal entries
  - Transformers library for advanced text analysis
  - Sentence Transformers for semantic search and document embeddings

### AI-Powered Features
- **Wellness Recommender System**:
  - Random Forest Classifier for personalized wellness recommendations
  - Evidence-based recommendation templates
  - Activity pattern analysis for contextual suggestions

- **Code Analysis Engine**:
  - Git commit pattern analysis
  - Code churn and contribution metrics
  - Development workflow optimization

### Generative AI Integration
- **Chat Assistant**:
  - LangChain for AI-powered conversation flows
  - Google Generative AI and OpenAI integration
  - Vector database (Chroma) for contextual memory and search

## 🏗️ Technical Architecture

### Backend
- **Web Framework**: Flask
- **Database**: SQLAlchemy ORM with SQLite/PostgreSQL
- **Authentication**: Flask-Login with secure password hashing

### Frontend
- **Templating**: Jinja2
- **Styling**: Custom CSS with responsive design
- **Interactive Elements**: JavaScript for dynamic content loading

### Data Processing
- **Code Analysis**: GitPython for repository mining
- **Time Series Analysis**: NumPy and Pandas for development metrics
- **Model Persistence**: Joblib for ML model serialization

## 🚀 Key Features

### Developer Wellness Dashboard
- Real-time activity tracking
- Wellness score visualization
- Personalized recommendations

### Code Repository Analysis
- Commit pattern analysis
- Code churn metrics
- Sentiment analysis of commits

### Intelligent Assistant
- Context-aware chat interface
- Documentation search
- Development guidance

## 🛠️ Setup and Installation

### Prerequisites
- Python 3.8+
- Git
- pip (Python package manager)

### Installation Steps
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd DevWell
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database:
   ```bash
   flask db upgrade
   ```

5. Run the development server:
   ```bash
   python app.py
   ```

6. Access the application at `http://localhost:5000`


## 📞 Contact
For questions or feedback, please reach out to our team at [mwangisimone007@gmail.com](mailto:mwangisimone007@gmail.com)
