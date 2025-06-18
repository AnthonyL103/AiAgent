import { useState } from 'react'

function App() {
  const [prompt, setPrompt] = useState('');
  const [conversation, setConversation] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

interface UserMessage {
    type: 'user';
    content: string;
    timestamp: Date;
}

interface AgentMessage {
    type: 'agent';
    content: string;
    timestamp: Date;
}

interface ErrorMessage {
    type: 'error';
    content: string;
    timestamp: Date;
}

type Message = UserMessage | AgentMessage | ErrorMessage;

const handleSubmit = async (e: React.FormEvent<HTMLFormElement> | React.KeyboardEvent<HTMLInputElement>): Promise<void> => {
    e.preventDefault();
    
    if (!prompt.trim()) return;

    setIsLoading(true);
    setError('');
    
    const userMessage: UserMessage = { type: 'user', content: prompt, timestamp: new Date() };
    setConversation((prev: Message[]) => [...prev, userMessage]);
    
    const currentPrompt = prompt;
    setPrompt(''); 

    try {
        const response: Response = await fetch("http://localhost:8000/get_prompt", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ prompt: currentPrompt }),
        });
        
        if (!response.ok) {
            throw new Error(`Failed to fetch: ${response.status}`);
        }
        
        const data = await response.json();
                
        
        if (data.type === 'human_input_required' || data.status === 'requires_input') {
            const agentMessage: AgentMessage = {
                type: 'agent',
                content: data.prompt,
                timestamp: new Date()
            };
            setConversation((prev: Message[]) => [...prev, agentMessage]);
        }
        
        else if (data.status === 'success' || data.type === 'normal_response') {
            const agentMessage: AgentMessage = {
                type: 'agent',
                content: data.result,
                timestamp: new Date()
            };
            setConversation((prev: Message[]) => [...prev, agentMessage]);
        }
       
        
        console.log("Agent response:", data);
        
    } catch (err: any) {
        console.error(err);
        setError(`Error: ${err.message}`);
        
        const errorMessage: ErrorMessage = { 
            type: 'error', 
            content: `Sorry, there was an error: ${err.message}`, 
            timestamp: new Date() 
        };
        setConversation((prev: Message[]) => [...prev, errorMessage]);
    } finally {
        setIsLoading(false);
    }
};

  const resetConversation = async () => {
    try {
      setIsLoading(true);
      const response = await fetch("http://localhost:8000/reset_conversation", {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        setConversation([]);
        setError('');
        console.log("Conversation reset successfully");
      } else {
        throw new Error('Failed to reset conversation');
      }
    } catch (err) {
      console.error("Error resetting conversation:", err);
      const errorMessage = (err instanceof Error) ? err.message : String(err);
      setError(`Failed to reset: ${errorMessage}`);
    } finally {
      setIsLoading(false);
    }
  };

interface KeyPressEvent extends React.KeyboardEvent<HTMLInputElement> {}

const handleKeyPress = (e: KeyPressEvent): void => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit(e);
    }
};

  return (
    <div className="flex flex-col min-h-screen min-w-screen bg-gray-100">
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full p-4">
        <div className="text-center py-6">
          <h1 className="text-3xl font-bold text-blue-600">Log Search Assistant</h1>
          <p className="text-gray-600 mt-2">Ask questions about your logs and metrics</p>
        </div>

        <div className="flex-1 bg-white rounded-lg shadow-lg mb-4 p-4 overflow-y-auto max-h-[65vh]">
          {conversation.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <h2 className="text-xl mb-2">Welcome! 👋</h2>
              <p>Start by asking a question about your logs or metrics.</p>
              <p className="text-sm mt-2">For example: "Show me errors from today" or "What's the status of the payment service?"</p>
            </div>
          ) : (
            <div className="space-y-4">
              {conversation.map((message, index) => (
                <div key={index} className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-3xl p-3 rounded-lg ${
                    message.type === 'user' 
                      ? 'bg-blue-500 text-white' 
                      : message.type === 'error'
                      ? 'bg-red-100 text-red-800 border border-red-300'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    <div className="whitespace-pre-wrap">{message.content}</div>
                    <div className={`text-xs mt-1 ${
                      message.type === 'user' ? 'text-blue-100' : 'text-gray-500'
                    }`}>
                      {message.timestamp.toLocaleTimeString()}
                    </div>
                  </div>
                </div>
              ))}
              
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 text-gray-800 p-3 rounded-lg">
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"></div>
                      <span>Searching logs...</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <div className="space-y-4">
          <div className="flex space-x-2">
            <input
              className="flex-1 bg-white h-12 rounded-lg text-black text-lg p-4 border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Ask about your logs or metrics..."
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
            />
            <button
              onClick={(e) => {
                const fakeEvent = {
                  preventDefault: () => {},
                } as React.FormEvent<HTMLFormElement>;
                handleSubmit(fakeEvent);
              }}
              disabled={isLoading || !prompt.trim()}
              className="bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
          
          <div className="flex justify-center space-x-4">
            <button
              onClick={resetConversation}
              disabled={isLoading}
              className="bg-gray-500 text-white px-4 py-2 rounded hover:bg-gray-600 disabled:bg-gray-400 disabled:cursor-not-allowed text-sm"
            >
              Reset Conversation
            </button>
          </div>
        </div>

        <div className="text-center text-sm text-gray-500 mt-4">
          <p>💡 You can ask follow-up questions - the assistant remembers our conversation!</p>
        </div>
      </div>
    </div>
  );
}

export default App;