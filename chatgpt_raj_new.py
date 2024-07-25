

import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import shutil
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_community.llms import CTransformers
from langchain.memory import ConversationBufferMemory
from langchain.chains import RetrievalQAWithSourcesChain
from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.exc import IntegrityError


app = Flask(__name__)
CORS(app)

# Define the database connection URL
username = 'user_raj'
password = 'system'
host = 'localhost'
database_name = 'chatgpt_db'

# Construct the database URL
db_url = f'mysql+mysqlconnector://{username}:{password}@{host}/{database_name}'

# Define a base class for declarative models
Base = declarative_base()
engine = create_engine(db_url)

# Define a data model (corresponds to the 'history' table)
class QueryResponse(Base):
    __tablename__ = 'history'
    id = Column(Integer, primary_key=True, autoincrement=True)
    query = Column(String(255))
    answer = Column(Text)

# Define a data model for the 'books' table
class Book(Base):
    __tablename__ = 'books'
    id = Column(Integer, primary_key=True, autoincrement=True)
    book_path = Column(String(255), unique=True)
    vector_path = Column(String(255))

    def __init__(self, book_path, vector_path):
        self.book_path = book_path
        self.vector_path = vector_path

# Create the database schema (if it doesn't exist)
Base.metadata.create_all(engine)

# Create a session to interact with the database
Session = sessionmaker(bind=engine)
session = Session()

UPLOAD_FOLDER = 'books'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Define the create_connection() function to establish a connection to the MySQL database
def create_connection():
    connection = None
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='chatgpt_db',
            user='user_raj',
            password='system'
        )
        print("Connected to MySQL database")
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
    return connection






class PDFChatBot:

    def __init__(self,db_faiss_path=None):
        self.data_path = os.path.join('books')
        # print(db_faiss_path)
        self.db_faiss_path = 'vectordb/db_faiss_RetractedMonitoringCardiovascularProblemsinHeartPatients'
        # self.db_faiss_path = str(db_faiss_path)
    

    def create_vector_db(self, file_path):
        # Extract filename and extension
        filename, file_extension = os.path.splitext(file_path)
        folder_name = f"db_faiss_{os.path.basename(filename)}"

        # Check if the folder already exists
        vector_db_path = os.path.join('vectordb', folder_name)
        if not os.path.exists(vector_db_path):
            os.makedirs(vector_db_path)

            loader = DirectoryLoader(self.data_path,
                                     glob='*.pdf',
                                     loader_cls=PyPDFLoader)

            documents = loader.load()
            text_splitter = RecursiveCharacterTextSplitter(chunk_size=400,
                                                       chunk_overlap=50)
            texts = text_splitter.split_documents(documents)

            embeddings = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2',
                                           model_kwargs={'device': 'cpu'})

            db = FAISS.from_documents(texts, embeddings)
            db.save_local(vector_db_path)

        return vector_db_path

    def load_llm(self):
        llm = CTransformers(
            model="./models/llama-2-7b-chat.ggmlv3.q8_0.bin",
            model_type="llama",
            max_new_tokens=2000,
            temperature=0.5
        )
        return llm

    def conversational_chain(self):
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2",
                                           model_kwargs={'device': 'cpu'})
        db = FAISS.load_local(self.db_faiss_path, embeddings, allow_dangerous_deserialization=True)

        memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
        conversational_chain = ConversationalRetrievalChain.from_llm( llm=self.load_llm(),
                                                                      retriever=db.as_retriever(search_kwargs={"k": 3}),
                                                                      verbose=True,
                                                                      memory=memory
                                                                      )

        system_template="""Only answer questions related to the following pieces of text.\n- Strictly not answer the question if user asked question is not present in the below text.
        Take note of the sources and include them in the answer in the format: "\nSOURCES: source1 \nsource2", use "SOURCES" in capital letters regardless of the number of sources.
        If you don't know the answer, just say that "I don't know", don't try to make up an answer.
        ----------------
        {summaries}"""
        messages = [
            SystemMessagePromptTemplate.from_template(system_template),
            HumanMessagePromptTemplate.from_template("{question}")
        ]
        prompt = ChatPromptTemplate.from_messages(messages)

        chain_type_kwargs = {"prompt": prompt}        
        conversational_chain1 = RetrievalQAWithSourcesChain.from_chain_type(
            llm=self.load_llm(),
            chain_type="stuff",
            retriever=db.as_retriever(search_kwargs={"k": 3}),
            return_source_documents=True
        )        

        return conversational_chain

# Initialize the chatbot before the Flask app starts listening for requests
chatbot = PDFChatBot()

@app.route('/ask', methods=['POST'])
def ask_question():
    global chatbot
    data = request.json
    print("Received data:", data)
    if 'question' not in data:
        return jsonify({'error': 'Question not provided.'}), 400

    question = data['question']
    result = chatbot.conversational_chain()({"question": question})
    serializable_result = {
        'answer': result.get('answer', ''),
        'source_documents': result.get('source_documents', []),
    }

    # Store query and response in the history table
    query_response = QueryResponse(query=question, answer=result.get('answer', ''))
    session.add(query_response)
    session.commit()

    return jsonify(serializable_result)

@app.route('/initialize', methods=['POST'])
def initialize_chatbot():
    return jsonify({'message': 'Chatbot initialized successfully!'})

@app.route('/pdf-files', methods=['GET'])
def get_pdf_files():
    connection = create_connection()
    pdf_files = []

    if connection:
        try:
            cursor = connection.cursor()
            sql_query = "SELECT book_path FROM books"
            cursor.execute(sql_query)
            pdf_files = [row[0] for row in cursor.fetchall()]
        except Error as e:
            print(f"Error fetching PDF files from MySQL database: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("MySQL connection closed")

    return jsonify(pdf_files)



@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)

    # Save file
    file.save(file_path)

    # Check if file path already exists in the database
    existing_book = session.query(Book).filter_by(book_path=file_path).first()
    if not existing_book:
        # Create a new vector database
        vector_db_path = chatbot.create_vector_db(file_path)
        
        # Save file path and vector database path to the database
        try:
            new_book = Book(book_path=file_path, vector_path=vector_db_path)
            session.add(new_book)
            session.commit()
            print("File path and vector database path saved to MySQL database")
        except IntegrityError:
            session.rollback()
            print("Error: File path already exists in the database")
    else:
        print("File path already exists in the database")

    return jsonify({'message': 'File uploaded successfully'})


@app.route('/select', methods=['POST'])
def select_file():
    global chatbot
    data = request.json
    if 'book_path' not in data:
        return jsonify({'error': 'Book path not provided.'}), 400

    book_path = data['book_path']

    try:
        # Connect to the database
        connection = create_connection()
        if connection:
            try:
                cursor = connection.cursor()

                # Select the vector_path corresponding to the provided book_path
                sql_query = "SELECT vector_path FROM books WHERE book_path = %s"
                cursor.execute(sql_query, (book_path,))
                result = cursor.fetchone()

                if result:
                    vector_path = result[0]
                    chatbot = PDFChatBot(vector_path)
                    return jsonify({'vector_path': vector_path})
                else:
                    return jsonify({'error': 'Book path not found in the database.'}), 404

            except Error as e:
                print(f"Error selecting vector_path from MySQL database: {e}")
                return jsonify({'error': 'Internal server error.'}), 500

            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    print("MySQL connection closed")
        else:
            print("Failed to connect to MySQL database")
            return jsonify({'error': 'Failed to connect to the database.'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/delete', methods=['POST'])
def delete_file():
    data = request.json
    if 'file_path' not in data:
        return jsonify({'error': 'File path not provided.'}), 400

    file_path = data['file_path']
    vector_path = os.path.join('vector', 'db_faiss')  # Adjust if your vector path is different

    try:
        # Delete the PDF file
        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            return jsonify({'error': 'File not found.'}), 404

        # Delete the vector files related to the PDF (customize this as per your vector storage)
        if os.path.exists(vector_path):
            shutil.rmtree(vector_path)

        # Remove file path from MySQL database
        connection = create_connection()
        if connection:
            try:
                cursor = connection.cursor()
                sql_query = "DELETE FROM books WHERE book_path = %s"
                cursor.execute(sql_query, (file_path,))
                connection.commit()
                print("File path removed from MySQL database")
            except Error as e:
                print(f"Error deleting file path from MySQL database: {e}")
            finally:
                if connection.is_connected():
                    cursor.close()
                    connection.close()
                    print("MySQL connection closed")
        else:
            print("Failed to connect to MySQL database")

        return jsonify({'message': 'File and vectors deleted successfully.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chat-history', methods=['GET'])
def get_chat_history():
    connection = create_connection()
    chat_history = []

    if connection:
        try:
            cursor = connection.cursor()
            sql_query = "SELECT id, query, answer FROM history ORDER BY id DESC"
            cursor.execute(sql_query)
            result = cursor.fetchall()
            chat_history = [{'id': row[0], 'query': row[1], 'answer': row[2]} for row in result]
        except Error as e:
            print(f"Error fetching chat history from MySQL database: {e}")
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("MySQL connection closed")

    return jsonify(chat_history)

@app.route('/remove-history/<int:history_id>', methods=['DELETE'])
def remove_chat_history(history_id):
    connection = create_connection()

    if connection:
        try:
            cursor = connection.cursor()
            sql_query = "DELETE FROM history WHERE id = %s"
            cursor.execute(sql_query, (history_id,))
            connection.commit()
            print("Chat history entry removed from MySQL database")
            return jsonify({'message': 'Chat history entry removed successfully'})
        except Error as e:
            print(f"Error removing chat history entry from MySQL database: {e}")
            return jsonify({'error': 'Failed to remove chat history entry'}), 500
        finally:
            if connection.is_connected():
                cursor.close()
                connection.close()
                print("MySQL connection closed")
    else:
        return jsonify({'error': 'Failed to connect to MySQL database'}), 500

if __name__ == '__main__':
    app.run(debug=True)






































