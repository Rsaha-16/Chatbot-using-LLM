import mysql.connector
from mysql.connector import Error
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import os
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

app = Flask(__name__)
CORS(app)

def create_connection():
    """Create a connection to MySQL database."""
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='mydb',
            user='laha',
            password='Laha_2002'
        )
        print("Connection to MySQL database successful")
        return connection
    except Error as e:
        print(f"Error connecting to MySQL database: {e}")
        return None

# MySQL database configuration
connection = create_connection()

UPLOAD_FOLDER = 'books'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


class PDFChatBot:

    def __init__(self):
        self.data_path = os.path.join('books')
        self.db_faiss_path = os.path.join('vector', 'db_faiss')

    def create_vector_db(self):
        '''function to create vector db provided the pdf files'''

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
        db.save_local(self.db_faiss_path)

    def load_llm(self):
        # Load the locally downloaded model here
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
        db = FAISS.load_local(self.db_faiss_path, embeddings,allow_dangerous_deserialization=True)
        # initializing the conversational chain
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
            #chain_type_kwargs=chain_type_kwargs
        )        

        return conversational_chain


chatbot = None


@app.route('/ask', methods=['POST'])
def ask_question():
    global chatbot
    if chatbot is None:
        return jsonify({'error': 'Chatbot not initialized. Please initialize first.'}), 500

    data = request.json
    print("Received data:", data)
    if 'question' not in data:
        return jsonify({'error': 'Question not provided.'}), 400

    question = data['question']
    result = chatbot.conversational_chain()({"question": question})

    # Log the query to the history table
    log_query(question)

    serializable_result = {
        'answer': result.get('answer', ''),
        'source_documents': result.get('source_documents', []),
        # Add more fields as needed
    }

    return jsonify(serializable_result)


def log_query(question):
    try:
        cursor = connection.cursor()
        sql_query = "INSERT INTO history (query) VALUES (%s)"
        cursor.execute(sql_query, (question,))
        connection.commit()
        print("Query logged to history table")
    except Error as e:
        print(f"Error logging query to history table: {e}")
        if connection.is_connected():
            cursor.close()
            print("MySQL connection closed")
        else:
            print("Failed to connect to MySQL database")

@app.route('/save_answer', methods=['POST'])
def save_answer_route():
    data = request.json
    if 'id' not in data or 'answer' not in data:
        return jsonify({'error': 'ID or answer not provided.'}), 400

    answer_id = data['id']
    answer = data['answer']

    try:
        cursor = connection.cursor()
        sql_query = "UPDATE history SET answer = %s WHERE id = %s"
        cursor.execute(sql_query, (answer, answer_id))
        connection.commit()
        print("Answer saved to history table")
    except Error as e:
        print(f"Error saving answer to history table: {e}")
        return jsonify({'error': 'Failed to save answer'}), 500
    finally:
        if connection.is_connected():
            cursor.close()

    return jsonify({'message': 'Answer saved successfully'})


@app.route('/initialize', methods=['POST'])
def initialize_chatbot():
    global chatbot
    print("Wait for a minute.")
    chatbot = PDFChatBot()
    chatbot.create_vector_db()
    return jsonify({'message': 'Chatbot initialized successfully!'})


@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))

    # Save file path to MySQL database
    try:
        cursor = connection.cursor()
        sql_query = "INSERT INTO books (book_path) VALUES (%s)"
        cursor.execute(sql_query, (os.path.join(app.config['UPLOAD_FOLDER'], file.filename),))
        connection.commit()
        print("File path saved to MySQL database")
    except Error as e:
        print(f"Error inserting file path into MySQL database: {e}")
        if connection.is_connected():
            cursor.close()
            print("MySQL connection closed")
        return jsonify({'error': 'Failed to save file path'}), 500

    return jsonify({'message': 'File uploaded successfully'})


@app.route('/get_pdf', methods=['GET'])
def get_pdf():
    try:
        cursor = connection.cursor()
        # Fetch file path from MySQL database
        cursor.execute("SELECT book_path FROM books ORDER BY id DESC LIMIT 1")
        file_path = cursor.fetchone()
        cursor.close()

        if file_path:
            # Return the PDF file
            return send_file(file_path[0], as_attachment=True)
        else:
            return jsonify({'error': 'No PDF file found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
