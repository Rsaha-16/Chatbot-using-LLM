import './App.css';

/*import React, { useState } from 'react';
import axios from 'axios';

const FileUpload = () => {
    const [selectedFile, setSelectedFile] = useState(null);

    const handleFileChange = (event) => {
        setSelectedFile(event.target.files[0]);
    };

    const handleUpload = () => {
        if (!selectedFile) {
            console.error('No file selected');
            return;
        }

        const formData = new FormData();
        formData.append('file', selectedFile);

        axios.post('http://127.0.0.1:5000/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            }
        })
        .then(response => {
            console.log(response.data);
            // Optionally, you can handle success message here
        })
        .catch(error => {
            console.error('Error uploading file:', error);
            // Optionally, you can handle error message here
        });
    };

    return (
        <div>
            <input type="file" onChange={handleFileChange} />
            <button onClick={handleUpload}>Upload</button>
        </div>
    );
};

export default FileUpload;*/
import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [question, setQuestion] = useState('');
  const [file, setFile] = useState(null);
  const [answer, setAnswer] = useState('');
  const [pdfFiles, setPdfFiles] = useState([]);

  useEffect(() => {
    // Fetch PDF files from MySQL database when the component mounts
    fetchPdfFiles();
  }, []);

  const fetchPdfFiles = async () => {
    try {
      const response = await axios.get('http://localhost:5000/pdf-files');
      setPdfFiles(response.data);
    } catch (error) {
      console.error('Error fetching PDF files:', error);
    }
  };

  const handleInitialize = async () => {
    try {
      const response = await axios.post('http://localhost:5000/initialize');
      console.log(response.data.message);
    } catch (error) {
      console.error('Error initializing PDFChatBot:', error);
    }
  };

  const handleAskQuestion = async () => {
    try {
      const response = await axios.post('http://localhost:5000/ask', { question });
      setAnswer(response.data.answer);
    } catch (error) {
      console.error('Error asking question:', error);
      setAnswer('Error asking question. Please try again.');
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    setFile(file);
  };

  const handleUpload = async () => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await axios.post('http://localhost:5000/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      console.log('File uploaded successfully:', response.data);
      // After successful upload, refetch PDF files to update the list
      fetchPdfFiles();
    } catch (error) {
      console.error('Error uploading file:', error);
    }
  };

  return (
    <div className="App">
      <h1>Chatbot UI</h1>
      <button onClick={handleInitialize}>Initialize PDFChatBot</button>
      <div>
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Enter your question..."
        />
        <button onClick={handleAskQuestion}>Ask</button>
      </div>
      <div>
        <input type="file" onChange={handleFileUpload} />
        <button onClick={handleUpload}>Upload</button>
      </div>
      {answer && <div><strong>Answer:</strong> {answer}</div>}
      <h2>List of PDF Files</h2>
      <ul className="pdf-list">
        {pdfFiles.map((pdfFile, index) => (
          <li key={index}>{pdfFile.split('/').pop()}</li>
        ))}
      </ul>
    </div>
  );
}

export default App;
