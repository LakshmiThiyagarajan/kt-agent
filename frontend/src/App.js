import { useState, useRef, useEffect } from "react";
import "./App.css";

function App() {
  const [activeMenu, setActiveMenu] = useState("home");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);

  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // ================= CHAT =================
  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg = { text: input, sender: "user" };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/ask", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userMsg.text }),
      });

      const data = await response.json();

      setMessages((prev) => [
        ...prev,
        { text: data.reply, sender: "bot" },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { text: "❌ Server error", sender: "bot" },
      ]);
    }

    setLoading(false);
  };

  // ================= UPLOAD =================
  const handleUpload = async () => {
    if (!selectedFile) {
      alert("Please select a file first");
      return;
    }

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const res = await fetch("http://127.0.0.1:8000/upload", {
        method: "POST",
        body: formData,
      });

      const data = await res.json();
      alert(`Uploaded: ${data.filename}`);
      setSelectedFile(null);
    } catch (err) {
      alert("Upload failed");
    }
  };

  return (
    <div className="app">
      {/* SIDEBAR */}
      <div className="sidebar">
        <h2>KT</h2>

        <div
          className={`menu ${activeMenu === "home" ? "active" : ""}`}
          onClick={() => setActiveMenu("home")}
        >
          🏠 Home
        </div>

        <div
          className={`menu ${activeMenu === "chat" ? "active" : ""}`}
          onClick={() => setActiveMenu("chat")}
        >
          💬 KT Assistant
        </div>

        <div
          className={`menu ${activeMenu === "upload" ? "active" : ""}`}
          onClick={() => setActiveMenu("upload")}
        >
          📤 Upload
        </div>
      </div>

      {/* MAIN */}
      <div className="main">
        <div className="header">
          {activeMenu === "home" && "Home"}
          {activeMenu === "chat" && "KT Assistant"}
          {activeMenu === "upload" && "Upload Document"}
        </div>

        <div className="content">
          {/* HOME */}
          {activeMenu === "home" && (
            <div className="center">
              <h2>Welcome to KT Assistant 👋</h2>
              <p style={{ maxWidth: "600px", margin: "20px auto", lineHeight: "1.6" }}>
                No more searching through files, screenshots or long documents.
                <br />
                Ask questions and let the assistant handle the rest.
              </p>
            </div>
          )}

          {/* CHAT */}
          {activeMenu === "chat" && (
            <div className="chat-wrapper">
              <div className="chat-area">
                {messages.map((msg, i) => (
                  <div key={i} className={`msg ${msg.sender}`}>
                    {msg.text}
                  </div>
                ))}
                {loading && <div className="msg bot">Typing...</div>}
                <div ref={chatEndRef} />
              </div>

              <div className="input-box">
                <input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Message KT Assistant..."
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                />
                <button onClick={sendMessage}>Send</button>
              </div>
            </div>
          )}

          {/* UPLOAD */}
          {activeMenu === "upload" && (
            <div className="center">
              <input
                type="file"
                onChange={(e) => setSelectedFile(e.target.files[0])}
              />
              <button onClick={handleUpload} style={{ marginTop: "10px" }}>
                Upload
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;