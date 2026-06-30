1.	 Introduction

1.1	Purpose
The purpose of this chess game is to make it playable for beginners and help them get better at it by using the difficulties such as easy mode and medium. This works as they play against an AI as an opponent. I am developing chess as it is my favourite board game since I was younger and want to make more people play this game as it requires a lot of thinking but also it is fun and competitive.


1.2	Problem Statement
Many beginner and intermediate chess players struggle to analyse their gameplay and identify mistakes. Existing tools are often complex or not easily accessible, limiting user improvement.


1.3	Proposed Solution
This project aims to develop a web-based application called ChessTrainer, which allows users to play chess against an AI engine and receive feedback on their moves. The system stores game data and provides analysis to support user improvement.





1.4	Target Users
The primary target users of this project are beginner chess players who are learning the fundamentals of the game and wish to develop their understanding of chess rules and basic strategies. The application is also designed for intermediate players seeking to improve their decision-making skills, tactical awareness and overall gameplay through practice against an AI opponent. In addition, students interested in learning chess strategies can use the program as an educational tool to analyse board positions, understand move evaluation scores and develop critical thinking and problem-solving skills in an engaging environment.



1.5	Success Criteria
The project will be considered successful if it allows users to play a complete game of chess from start to finish with all standard chess rules functioning correctly. The system should include an AI opponent that automatically responds to the player’s moves, creating an interactive and challenging gameplay experience. An evaluation score should be displayed during the game to provide players with insight into the current board position and which side holds the advantage. Additionally, the program should offer multiple difficulty levels, allowing users of different skill levels to adjust the challenge and improve their gameplay over time. These success criteria will ensure the application is functional, engaging and meets the objectives of the project.















2.	Requirements Analysis
Requirements analysis identifies what the software must do and the standards it must meet. This process ensures the Chess AI Trainer satisfies the needs of users while remaining practical to develop using the available tools and resources.


2.1	Functional Requirements
Functional requirements describe the specific features and operations the system must perform.

FR1 – Move Pieces
The system must allow users to move chess pieces around the board according to the rules of chess. Players select a piece and choose a destination square. Once a valid move is chosen, the board updates to reflect the new position.
This requirement is achieved through the interaction between the Board, Move, and Piece classes, which manage piece positions and movement across the chessboard.

FR2 – Validate Legal Moves
The system must ensure that players can only perform legal chess moves. Invalid moves should be rejected automatically.
For example, a bishop may only move diagonally, while a knight moves in an L-shape. The move validation system checks whether a selected move follows the rules of the piece before allowing it to be executed.
This functionality is implemented in the calc_moves() and valid_move() methods within the Board class.

FR3 – AI Opponent
The system must provide an artificial intelligence opponent capable of automatically generating moves after the player completes their turn.
The AI analyses the current board position and selects a move based on a board evaluation algorithm. This allows users to practise chess without requiring a second player.
The feature is implemented through the ChessAI class.

FR4 – Difficulty Selection
The system must allow users to select different difficulty levels before beginning a game.
Difficulty settings provide users with varying levels of challenge and improve the educational value of the application. Beginner players can select Easy mode, while more experienced users can select Medium mode.
Difficulty selection is available through the start menu and affects the AI decision-making process.

FR5 – Game Reset
The system must provide a reset function that returns the board to its starting position.
This allows users to quickly begin a new game without restarting the application. The reset feature improves usability and assists during testing and debugging.
The feature is activated using the keyboard shortcut and reinitialises all game objects.

FR6 – Piece Capture
The system must support the capture of opponent pieces.
When a piece moves onto a square occupied by an opposing piece, the opposing piece is removed from the board. Capture functionality is a fundamental requirement of chess and contributes to gameplay realism.
The system also plays a capture sound effect to provide visual and audio feedback to the user.














2.2	Non-Functionable Requirements
Non-functional requirements describe the quality standards the software must achieve.

NFR1 – Fast Performance
The application must respond quickly to user actions and AI calculations.
Moves should occur immediately after selection, and the AI should generate responses within a reasonable time frame. Slow performance would negatively affect the user experience.
Python and Pygame provide sufficient performance for a school-scale chess application.

NFR2 – Easy to Use
The interface must be simple and intuitive for beginner users.
Players should be able to start a game, move pieces, select a difficulty level and reset the board without requiring technical knowledge. Clear graphics and straightforward controls improve accessibility.

NFR3 – Reliable
The system must operate consistently without crashes or unexpected behaviour.
Reliability is particularly important during gameplay because incorrect move validation or application crashes would reduce user confidence and affect the educational value of the software.
Extensive testing was conducted to ensure reliability.

NFR4 – Maintainable
The software must be structured in a way that allows future modifications and improvements.
Object-oriented programming principles were used to separate responsibilities into classes such as Board, Game, Piece, and ChessAI. This modular design makes the program easier to debug, extend and maintain.






2.3	Constraints
Constraints are limitations that affect the development of the project.

C1 – Python
The project was required to be developed using Python due to its simplicity, readability and strong support for object-oriented programming. Python also provides numerous libraries suitable for game development and artificial intelligence.

C2 – Pygame
The graphical user interface was developed using the Pygame library. While Pygame provides effective tools for creating games, it is less advanced than professional game engines such as Unity or Unreal Engine. This limited some graphical features that could be implemented.

C3 – School Hardware
The software needed to run efficiently on standard school computers without requiring specialised hardware.
As a result, the AI algorithm was intentionally kept lightweight to ensure smooth performance across all available devices.



















3.	Research
Before developing the Chess AI Trainer, research was conducted into chess rules, artificial intelligence algorithms and existing chess platforms. This research helped determine the features, design decisions and implementation methods used throughout the project.



3.1	Chess Rules Research
A thorough understanding of chess rules was required before development could begin. The application needed to accurately replicate the movement patterns and gameplay mechanics of a real chess match.

Research was conducted into the movement rules of all six chess pieces:
•	Pawn 
•	Rook 
•	Knight 
•	Bishop 
•	Queen 
•	King 

Special chess rules were also investigated, including:
•	Castling 
•	Pawn promotion 
•	En passant 
•	Check 
•	Checkmate 
•	Stalemate 

Understanding these rules was essential because the move validation system relies on them to determine whether a player's move is legal. Incorrect implementation would result in unrealistic gameplay and reduce the educational value of the application.
The research also highlighted the importance of preventing illegal moves that place a player's king in check. This influenced the design of the move generation and validation algorithms within the Board class.



3.2	AI Algorithms Research
One of the main goals of the project was to provide a computer-controlled opponent. Several artificial intelligence approaches were investigated before selecting the final implementation.

1.	Minimax Algorithm
The Minimax algorithm is one of the most widely used decision-making algorithms in chess engines.
Minimax works by exploring future board positions and assuming that both players make the best possible moves. The algorithm attempts to maximise the AI's advantage while minimising the opponent's advantage.

Advantages:
•	Produces stronger gameplay 
•	Can analyse multiple future moves 
•	Used in professional chess engines 

Disadvantages:
•	Computationally expensive 
•	Difficult to implement efficiently 
•	Requires significant processing power 

Due to the project's time constraints and the limitations of school hardware, a full Minimax implementation was considered too complex for the current version of the application.

However, research into Minimax influenced the design of the evaluation system and may be implemented in future versions.


2.	Random Move AI
Random Move AI selects a legal move at random from all available moves.

Advantages:
•	Very easy to implement 
•	Fast performance 
•	Suitable for beginners 



Disadvantages:
•	Makes poor strategic decisions 
•	Easily defeated 
•	Provides limited challenge 

While Random Move AI offers excellent performance, it does not provide a realistic chess experience. Therefore, it was not selected as the primary AI strategy.


3.	Evaluation Functions
An evaluation function assigns a numerical value to a board position.

The AI analyses the pieces remaining on the board and calculates which player has an advantage.

Research showed that most chess engines use piece values similar to:
Piece	Value
Pawn	1
Knight	3
Bishop	3
Rook	5
Queen	9
King	Very High Value
	
This approach was adopted in the project's ChessAI class.

The evaluation score is displayed on-screen to provide users with feedback regarding which side currently holds the advantage.

The evaluation function provided a balance between simplicity and effectiveness while remaining suitable for school-level hardware.







3.3	Similar Products
Research was conducted into existing chess platforms to identify useful features and industry standards.
Chess.com
Chess.com is one of the world's largest online chess platforms.
Key features include:
•	Online multiplayer 
•	Computer opponents 
•	Puzzle training 
•	Performance analysis 
•	Player rankings 
The platform demonstrated the importance of providing AI opponents for practice and skill development.
However, many of its advanced features were beyond the scope of this project.

Lichess
Lichess is a free and open-source online chess platform.
Key features include:
•	Free analysis tools 
•	Online play 
•	Opening explorer 
•	Training exercises 
•	Study resources 
Research into Lichess highlighted the value of simplicity and accessibility. Its clean user interface influenced the design goal of creating an easy-to-use application for beginner players.

Stockfish
Stockfish is one of the strongest chess engines in the world.
Key features include:
•	Advanced search algorithms 
•	Deep position analysis 
•	Extremely high playing strength 
•	Open-source development 
Although Stockfish is significantly more sophisticated than this project, researching its architecture provided insight into how chess engines evaluate positions and generate moves.
The project uses a simplified evaluation-based AI inspired by the principles used in professional engines such as Stockfish.
Research Conclusion
The research phase demonstrated that successful chess applications require accurate rule implementation, efficient move validation and intelligent decision-making. While advanced algorithms such as Minimax and Stockfish-style search were beyond the scope of this project, the evaluation-based AI provides a suitable balance between performance and functionality. Research into existing chess platforms also influenced the decision to prioritise usability, educational value and accessibility for beginner players.
