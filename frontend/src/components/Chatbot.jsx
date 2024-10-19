import React, { useState, useRef, useEffect } from 'react';
import { Send, Code, Bot, Link as LinkIcon } from 'lucide-react';

const Chatbot = () => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const sendMessage = async () => {
    if (input.trim() === '') return;

    const userMessage = { text: input, sender: 'user' };
    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:5000/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: input }),
      });

      const data = await response.json();

      if (data.error) {
        setMessages(msgs => [...msgs, { text: `Error: ${data.error}`, sender: 'bot' }]);
      } else {
        setMessages(msgs => [
          ...msgs,
          { text: data.most_relevant_code, sender: 'bot', type: 'code' },
          { text: `Similarity Score: ${data.similarity_score.toFixed(2)}`, sender: 'bot' },
          { text: `File Link: ${data.file_link}`, sender: 'bot', type: 'link' },
        ]);
      }
    } catch (error) {
      setMessages(msgs => [...msgs, { text: `Error: ${error.message}`, sender: 'bot' }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6 shadow-lg">
        <h1 className="text-3xl font-bold flex items-center justify-center">
          <Bot className="mr-3" size={32} /> Code Snippet Searcher
        </h1>
      </div>
      <div className="flex-grow overflow-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl p-4 shadow-md ${
                message.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-white'
              }`}>
                {message.type === 'code' && (
                  <div className="flex items-center space-x-2 mb-2">
                    <Code size={18} className="text-yellow-400" />
                    <span className="font-semibold text-sm text-yellow-400">Code Snippet</span>
                  </div>
                )}
                {message.type === 'link' && (
                  <div className="flex items-center space-x-2 mb-2">
                    <LinkIcon size={18} className="text-green-400" />
                    <span className="font-semibold text-sm text-green-400">File Link</span>
                  </div>
                )}
                {message.type === 'code' ? (
                  <pre className="text-sm bg-gray-800 text-green-400 p-3 rounded-lg overflow-x-auto"><code>{message.text}</code></pre>
                ) : message.type === 'link' ? (
                  <a href={message.text.split(': ')[1]} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                    {message.text}
                  </a>
                ) : (
                  <p className={message.sender === 'user' ? 'text-white' : 'text-gray-800'}>{message.text}</p>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <div className="bg-white border-t p-6 shadow-lg">
        <div className="max-w-3xl mx-auto flex space-x-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="Ask about your code..."
            className="flex-grow p-3 border border-gray-300 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={isLoading}
            className="bg-blue-500 hover:bg-blue-600 text-white p-3 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors duration-200"
          >
            {isLoading ? (
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white"></div>
            ) : (
              <Send size={24} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;