
// import './App.css';

// import React, { useState, useEffect } from 'react';
// import axios from 'axios';

// function App() {
//   const [question, setQuestion] = useState('');
//   const [file, setFile] = useState(null);
//   const [answer, setAnswer] = useState('');
//   const [pdfFiles, setPdfFiles] = useState([]);
//   const [chatHistory, setChatHistory] = useState([]);
//   const [searchQuery, setSearchQuery] = useState('');
//   const [searchResults, setSearchResults] = useState([]);

//   useEffect(() => {
//     // Fetch PDF files from MySQL database when the component mounts
//     fetchPdfFiles();
//     fetchChatHistory();
//   }, []);

//   const fetchChatHistory = async () => {
//     try {
//       const response = await axios.get('http://localhost:5000/chat-history');
//       setChatHistory(response.data);
//     } catch (error) {
//       console.error('Error fetching chat history:', error);
//     }
//   };

//   const fetchPdfFiles = async () => {
//     try {
//       const response = await axios.get('http://localhost:5000/pdf-files');
//       setPdfFiles(response.data);
//     } catch (error) {
//       console.error('Error fetching PDF files:', error);
//     }
//   };

//   const handleInitialize = async () => {
//     try {
//       const response = await axios.post('http://localhost:5000/initialize');
//       console.log(response.data.message);
//     } catch (error) {
//       console.error('Error initializing PDFChatBot:', error);
//     }
//   };

//   const handleAskQuestion = async () => {
//     try {
//       const response = await axios.post('http://localhost:5000/ask', { question });
//       const fullAnswer = response.data.answer;
//       let currentAnswer = '';
  
//       for (let i = 0; i < fullAnswer.length; i++) {
//         // Update the answer gradually
//         currentAnswer += fullAnswer[i];
//         setAnswer(currentAnswer);
//         await new Promise(resolve => setTimeout(resolve, 100)); // Delay between each letter (adjust as needed)
//       }
//     } catch (error) {
//       console.error('Error asking question:', error);
//       setAnswer('Error asking question. Please try again.');
//     }
//   };
  

//   const handleFileUpload = (event) => {
//     const file = event.target.files[0];
//     setFile(file);
//   };

//   const handleUpload = async () => {
//     try {
//       const formData = new FormData();
//       formData.append('file', file);
//       const response = await axios.post('http://localhost:5000/upload', formData, {
//         headers: {
//           'Content-Type': 'multipart/form-data'
//         }
//       });
//       console.log('File uploaded successfully:', response.data);
//       // After successful upload, refetch PDF files to update the list
//       fetchPdfFiles();
//     } catch (error) {
//       console.error('Error uploading file:', error);
//     }
//   };

//   const handleDelete = async (filePath) => {
//     try {
//       const response = await axios.post('http://localhost:5000/delete', { file_path: filePath });
//       console.log('File deleted successfully:', response.data);
//       fetchPdfFiles();
//     } catch (error) {
//       console.error('Error deleting file:', error);
//     }
//   };
//   const handleSelect = async (filePath) => {
//     try {
//       const response = await axios.post('http://localhost:5000/select', { book_path: filePath });
//       console.log('File selected successfully:', response.data.vector_path);
//       fetchPdfFiles();
//     } catch (error) {
//       console.error('Error selecting file:', error);
//     }
//   };
  
//   const handleShowAnswer = async (questionId) => {
//     try {
//       const response = await axios.get(`http://localhost:5000/chat-history/${questionId}`);
//       const updatedChatHistory = chatHistory.map((chat) => {
//         if (chat.id === questionId) {
//           return { ...chat, answer: response.data.answer };
//         }
//         return chat;
//       });
//       setChatHistory(updatedChatHistory);
//     } catch (error) {
//       console.error('Error fetching answer:', error);
//     }
//   };

//   const handleRemoveHistory = async (historyId) => {
//     try {
//       const response = await axios.delete(`http://localhost:5000/remove-history/${historyId}`);
//       console.log(response.data.message);
//       fetchChatHistory(); // Refresh chat history after removing entry
//     } catch (error) {
//       console.error('Error removing chat history:', error);
//     }
//   };

//   const handleSearch = async () => {
//     try {
//       const response = await axios.post('http://localhost:5000/search-history', { query: searchQuery });
//       setSearchResults(response.data);
//     } catch (error) {
//       console.error('Error searching history:', error);
//     }
//   };

//   return (
//     <div className="App">
//       <div className="sidebar-left">
//         <h1>Upload pdf files here</h1>
//         <div className="file-upload-section">
//           <input className="file-input" type="file" onChange={handleFileUpload} multiple />
//           <button className="btn-primary" onClick={handleUpload}>Upload</button>

//           <h2>List of PDF Files</h2>
//           <ul className="pdf-list">
//                 {pdfFiles.map((pdfFile, index) => (
//                   <li key={index} className="pdf-list-item">
//                     <div className="pdf-name" title={pdfFile.split('/').pop()}>
//                       {pdfFile.split('/').pop()}
//                     </div>
//                     <button className="btn-select" onClick={() => handleSelect(pdfFile)}>Select</button>
//                     <button className="btn-delete" onClick={() => handleDelete(pdfFile)}>Delete</button>
//                   </li>
//                 ))}
//               </ul>
//         </div>
//       </div>

//       <div className="sidebar-right">
//         <h1>Search Chat History</h1>
//         <div className="search-section">
//           <input
//             type="text"
//             value={searchQuery}
//             onChange={(e) => setSearchQuery(e.target.value)}
//             placeholder="Enter your search query..."
//           />
//           <button className="btn-primary" onClick={handleSearch}>Search</button>
//         </div>
//         <div className="search-results">
//           <h2>Search Results</h2>
//           <ul>
//             {searchResults.map((result, index) => (
//               <li key={index}>
//                 <strong>Q:</strong> {result.query}
//                 <p><strong>A:</strong> {result.answer}</p>
//               </li>
//             ))}
//           </ul>
//         </div>
//       </div>


//       <div className="main-content">
//         <h1>Welcome to our Llama Chatbot</h1>
//         <button className="btn-primary" onClick={handleInitialize}>Initialize PDFChatBot</button>
//         <div className="question-section">
//           <input
//             type="text"
//             value={question}
//             onChange={(e) => setQuestion(e.target.value)}
//             placeholder="Enter your question..."
//           />
//           <button className="btn-primary" onClick={handleAskQuestion}>Ask</button>
//         </div>
//       <div className="chat-history">
//             <h2>Chat History</h2>
//             <ul>
//             {answer && (
//       <div className="answer-section">
//         <strong style={{ marginRight: '8px' }}>Answer</strong>
//         <div>{answer}</div>
//       </div>
//     )}
//               {chatHistory.map((chat, index) => (
//                 <li key={index}>
//                   <strong>Q:</strong> {chat.query}
//                   {chat.answer && <p><strong>A:</strong> {chat.answer}</p>}
//                   {chat.answer ? null : <button onClick={() => handleShowAnswer(chat.id)}>Show Answer</button>}
//                   <button onClick={() => handleRemoveHistory(chat.id)}>Remove</button>
//                 </li>
//               ))}
//             </ul>
//           </div>
//       </div>
//     </div>

//   );
// }

// export default App;






import React from 'react';
// import { BrowserRouter as Router, Route, Switch } from 'react-router-dom'; // Only import Switch once
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom';

import Login from './Login';
import Main from './Main'; // This is your existing main component (File 2)

function App() {
  return (
    <Router>
      <Switch>
        <Route exact path="/" component={Login} />
        <Route path="/main" component={Main} />
      </Switch>
    </Router>
  );
}

export default App;




























