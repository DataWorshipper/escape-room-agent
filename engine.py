import json

def load_scenario(path):
    with open(path,"r",encoding="utf-8") as f:
        return json.load(f)

def normalize(text):
    return " ".join(text.lower().split())

class Game:
    def __init__(self,scenario):
        self.name=scenario["name"]
        self.intro = scenario["intro"]
        self.manual = scenario["manual"]
        self.modules=scenario["modules"]
        self.max_strikes = scenario.get("max_strikes", 3)
        self.current=0
        self.strikes=0
        self.status="playing"
        self.messages=[]
        self.read_counts = {}
        self.notebooks={}
    
    def look(self):
        if self.current >= len(self.modules):
            return "The panel is fully reset. The doors are unlocked!"

        module=self.modules[self.current]
        return (
            f"Module {self.current + 1} of {len(self.modules)} - "
            f"{module['title']}\n\n"
            f"{module['observation']}"
        )
    def read_manual(self):
        return self.manual
    
    def submit(self,action):
        if self.status!="playing":
            return f"Game already ended ({self.status})"
        module = self.modules[self.current]
        if self.is_correct(module, action):
            self.current += 1
            if self.current >= len(self.modules):
                self.status = "won"
                return "Correct! Panel disarmed. You escaped."

            return f"Correct! {len(self.modules)-self.current} modules left."

      
        self.strikes += 1

        if self.strikes >= self.max_strikes:
            self.status = "lost"
            return "Strike limit reached. Game Over."

        return f"Wrong! Strike {self.strikes}/{self.max_strikes}"
    
    def is_correct(self, module, action):

        guess = normalize(action)

        acceptable = [
            module["answer"],
            *module.get("accept", [])
        ]

        return any(
            normalize(ans) in guess
            for ans in acceptable
        )
    
    def send_message(self, sender, text):

        self.messages.append({
            "sender": sender,
            "text": text
        })

        return "Message sent."

    def read_messages(self, receiver):
        seen = self.read_counts.get(receiver, 0)
        new = self.messages[seen:]
        self.read_counts[receiver] = len(self.messages)
        incoming = [f"{m['sender']}: {m['text']}" for m in new if m["sender"] != receiver]
        if not incoming:
            return "No new messages."
        return "\n".join(incoming)

    def remember(self, agent, note):

        self.notebooks.setdefault(agent, []).append(note)

        return "Noted."

    def recall(self, agent):
        notes = self.notebooks.setdefault(agent, [])
        if not notes:
            return "Notebook empty."

        return "\n".join(notes)

    def state(self):
        return {
            "status": self.status,
            "current_module": self.current,
            "total_modules": len(self.modules),
            "strikes": self.strikes,
            "max_strikes": self.max_strikes,
        }

    
    def is_over(self):
        return self.status != "playing"
    
    
        
        
            
        
        
        
        
        