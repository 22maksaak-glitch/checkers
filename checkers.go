// checkers.go
// Версия на Go с использованием структур, методов, цветного вывода, сохранения/загрузки JSON

package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"math/rand"
	"os"
	"regexp"
	"strconv"
	"strings"
	"time"
)

// Цвета ANSI
const (
	reset  = "\033[0m"
	black  = "\033[30m"
	red    = "\033[31m"
	green  = "\033[32m"
	yellow = "\033[33m"
	blue   = "\033[34m"
	magenta = "\033[35m"
	cyan   = "\033[36m"
	white  = "\033[37m"
	bgBlack = "\033[40m"
	bgWhite = "\033[47m"
)

func colorize(text string, fg string, bg string) string {
	bgCode := ""
	if bg == "black" {
		bgCode = bgBlack
	} else if bg == "white" {
		bgCode = bgWhite
	}
	return fg + bgCode + text + reset
}

type ColorType int
const (
	WHITE ColorType = 1
	BLACK ColorType = 2
)

type PieceType int
const (
	MAN PieceType = 1
	KING PieceType = 2
)

type Piece struct {
	Color ColorType
	Type  PieceType
}

type Move struct {
	FromRow  int
	FromCol  int
	ToRow    int
	ToCol    int
	Captures [][2]int
}

type Board struct {
	grid [10][10]*Piece
}

func NewBoard() *Board {
	b := &Board{}
	for r := 0; r < 10; r++ {
		for c := 0; c < 10; c++ {
			if (r+c)%2 == 1 {
				if r < 4 {
					b.grid[r][c] = &Piece{WHITE, MAN}
				} else if r > 5 {
					b.grid[r][c] = &Piece{BLACK, MAN}
				}
			}
		}
	}
	return b
}

func (b *Board) inBounds(r, c int) bool {
	return r >= 0 && r < 10 && c >= 0 && c < 10
}

func (b *Board) GetPiece(r, c int) *Piece {
	if b.inBounds(r, c) {
		return b.grid[r][c]
	}
	return nil
}

func (b *Board) IsOccupied(r, c int) bool {
	return b.GetPiece(r, c) != nil
}

func (b *Board) PlacePiece(r, c int, p *Piece) {
	b.grid[r][c] = p
}

func (b *Board) RemovePiece(r, c int) {
	b.grid[r][c] = nil
}

func (b *Board) FindPieces(color ColorType) [][2]int {
	var res [][2]int
	for r := 0; r < 10; r++ {
		for c := 0; c < 10; c++ {
			if p := b.grid[r][c]; p != nil && p.Color == color {
				res = append(res, [2]int{r, c})
			}
		}
	}
	return res
}

func (b *Board) IsKingRow(r int, color ColorType) bool {
	return (color == WHITE && r == 9) || (color == BLACK && r == 0)
}

func (b *Board) PromoteToKing(r, c int) {
	if p := b.grid[r][c]; p != nil && p.Type == MAN {
		b.grid[r][c] = &Piece{p.Color, KING}
	}
}

func (b *Board) Clone() *Board {
	nb := NewBoard()
	for r := 0; r < 10; r++ {
		for c := 0; c < 10; c++ {
			if p := b.grid[r][c]; p != nil {
				nb.grid[r][c] = &Piece{p.Color, p.Type}
			} else {
				nb.grid[r][c] = nil
			}
		}
	}
	return nb
}

type Game struct {
	board       *Board
	currentTurn ColorType
	twoPlayers  bool
	moveHistory []Move
}

func NewGame(twoPlayers bool) *Game {
	return &Game{
		board:       NewBoard(),
		currentTurn: WHITE,
		twoPlayers:  twoPlayers,
		moveHistory: []Move{},
	}
}

func (g *Game) opponent(color ColorType) ColorType {
	if color == WHITE {
		return BLACK
	}
	return WHITE
}

func (g *Game) getManMoves(row, col int, color ColorType) []Move {
	var moves []Move
	dirs := [][2]int{}
	if color == WHITE {
		dirs = [][2]int{{1, -1}, {1, 1}}
	} else {
		dirs = [][2]int{{-1, -1}, {-1, 1}}
	}
	for _, d := range dirs {
		nr, nc := row+d[0], col+d[1]
		if g.board.inBounds(nr, nc) && !g.board.IsOccupied(nr, nc) {
			moves = append(moves, Move{row, col, nr, nc, [][2]int{}})
		}
	}
	for _, dr := range []int{-1, 1} {
		for _, dc := range []int{-1, 1} {
			nr, nc := row+dr, col+dc
			if g.board.inBounds(nr, nc) {
				target := g.board.GetPiece(nr, nc)
				if target != nil && target.Color != color {
					jr, jc := nr+dr, nc+dc
					if g.board.inBounds(jr, jc) && !g.board.IsOccupied(jr, jc) {
						moves = append(moves, Move{row, col, jr, jc, [][2]int{{nr, nc}}})
					}
				}
			}
		}
	}
	return moves
}

func (g *Game) getKingMoves(row, col int, color ColorType) []Move {
	var moves []Move
	for _, dr := range []int{-1, 1} {
		for _, dc := range []int{-1, 1} {
			// simple moves
			r, c := row+dr, col+dc
			for g.board.inBounds(r, c) {
				if g.board.IsOccupied(r, c) {
					break
				}
				moves = append(moves, Move{row, col, r, c, [][2]int{}})
				r += dr
				c += dc
			}
			// captures
			r, c = row+dr, col+dc
			for g.board.inBounds(r, c) {
				if g.board.IsOccupied(r, c) {
					target := g.board.GetPiece(r, c)
					if target != nil && target.Color != color {
						br, bc := r+dr, c+dc
						for g.board.inBounds(br, bc) {
							if g.board.IsOccupied(br, bc) {
								break
							}
							moves = append(moves, Move{row, col, br, bc, [][2]int{{r, c}}})
							break
						}
					}
					break
				}
				r += dr
				c += dc
			}
		}
	}
	return moves
}

func (g *Game) GetAllValidMoves(color ColorType) []Move {
	pieces := g.board.FindPieces(color)
	var moves []Move
	for _, p := range pieces {
		r, c := p[0], p[1]
		piece := g.board.GetPiece(r, c)
		if piece == nil {
			continue
		}
		if piece.Type == MAN {
			moves = append(moves, g.getManMoves(r, c, color)...)
		} else {
			moves = append(moves, g.getKingMoves(r, c, color)...)
		}
	}
	var captures []Move
	for _, m := range moves {
		if len(m.Captures) > 0 {
			captures = append(captures, m)
		}
	}
	if len(captures) > 0 {
		return captures
	}
	return moves
}

func (g *Game) IsValidMove(move Move) bool {
	all := g.GetAllValidMoves(g.currentTurn)
	for _, m := range all {
		if m.FromRow == move.FromRow && m.FromCol == move.FromCol &&
			m.ToRow == move.ToRow && m.ToCol == move.ToCol {
			if len(m.Captures) == len(move.Captures) {
				// compare sets
				set1 := make(map[[2]int]bool)
				for _, cap := range m.Captures {
					set1[cap] = true
				}
				set2 := make(map[[2]int]bool)
				for _, cap := range move.Captures {
					set2[cap] = true
				}
				ok := true
				for k := range set1 {
					if !set2[k] {
						ok = false
						break
					}
				}
				if ok {
					return true
				}
			}
		}
	}
	return false
}

func (g *Game) MakeMove(move Move) bool {
	if !g.IsValidMove(move) {
		return false
	}
	piece := g.board.GetPiece(move.FromRow, move.FromCol)
	if piece == nil {
		return false
	}
	g.board.RemovePiece(move.FromRow, move.FromCol)
	g.board.PlacePiece(move.ToRow, move.ToCol, piece)
	for _, cap := range move.Captures {
		g.board.RemovePiece(cap[0], cap[1])
	}
	if g.board.IsKingRow(move.ToRow, piece.Color) && piece.Type == MAN {
		g.board.PromoteToKing(move.ToRow, move.ToCol)
	}
	g.moveHistory = append(g.moveHistory, move)
	g.currentTurn = g.opponent(g.currentTurn)
	return true
}

func (g *Game) IsGameOver() *ColorType {
	white := g.board.FindPieces(WHITE)
	black := g.board.FindPieces(BLACK)
	if len(white) == 0 {
		res := BLACK
		return &res
	}
	if len(black) == 0 {
		res := WHITE
		return &res
	}
	moves := g.GetAllValidMoves(g.currentTurn)
	if len(moves) == 0 {
		res := g.opponent(g.currentTurn)
		return &res
	}
	return nil
}

func (g *Game) ParseMove(input string) *Move {
	parts := strings.Fields(input)
	if len(parts) < 2 {
		return nil
	}
	coords := [][2]int{}
	re := regexp.MustCompile(`^([A-Ja-j])([1-9]|10)$`)
	for _, p := range parts {
		m := re.FindStringSubmatch(p)
		if m == nil {
			return nil
		}
		col := int(m[1][0] - 'A')
		if m[1][0] >= 'a' {
			col = int(m[1][0] - 'a')
		}
		row, _ := strconv.Atoi(m[2])
		row--
		coords = append(coords, [2]int{row, col})
	}
	if len(coords) < 2 {
		return nil
	}
	from := coords[0]
	to := coords[len(coords)-1]
	var captures [][2]int
	for i := 0; i < len(coords)-1; i++ {
		r1, c1 := coords[i][0], coords[i][1]
		r2, c2 := coords[i+1][0], coords[i+1][1]
		if abs(r2-r1) != abs(c2-c1) {
			return nil
		}
		dr := 1
		if r2 < r1 {
			dr = -1
		}
		dc := 1
		if c2 < c1 {
			dc = -1
		}
		cr, cc := r1+dr, c1+dc
		for cr != r2 || cc != c2 {
			piece := g.board.GetPiece(cr, cc)
			if piece == nil || piece.Color == g.currentTurn {
				return nil
			}
			captures = append(captures, [2]int{cr, cc})
			cr += dr
			cc += dc
		}
	}
	return &Move{from[0], from[1], to[0], to[1], captures}
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func (g *Game) Display(useColor bool) {
	fmt.Print("  ")
	for c := 0; c < 10; c++ {
		fmt.Printf("%c ", 'A'+c)
	}
	fmt.Println()
	for r := 9; r >= 0; r-- {
		fmt.Printf("%2d ", r+1)
		for c := 0; c < 10; c++ {
			piece := g.board.GetPiece(r, c)
			bg := "black"
			if (r+c)%2 == 0 {
				bg = "white"
			}
			if piece == nil {
				if useColor {
					fmt.Print(colorize(" . ", reset, bg))
				} else {
					fmt.Print(" . ")
				}
			} else {
				sym := "W"
				if piece.Color == BLACK {
					sym = "B"
				}
				if piece.Type == KING {
					sym += "*"
				} else {
					sym += " "
				}
				fg := "black"
				if bg == "black" {
					fg = "white"
				}
				if useColor {
					fmt.Print(colorize(sym, fg, bg))
				} else {
					fmt.Print(sym + " ")
				}
			}
		}
		fmt.Println()
	}
	turn := "Белые"
	if g.currentTurn == BLACK {
		turn = "Чёрные"
	}
	fmt.Printf("Ход: %s\n", turn)
}

func (g *Game) GetAIMove() *Move {
	moves := g.GetAllValidMoves(g.currentTurn)
	if len(moves) == 0 {
		return nil
	}
	var captures []Move
	for _, m := range moves {
		if len(m.Captures) > 0 {
			captures = append(captures, m)
		}
	}
	if len(captures) > 0 {
		return &captures[rand.Intn(len(captures))]
	}
	return &moves[rand.Intn(len(moves))]
}

type serializedBoard [10][10]*PieceData
type PieceData struct {
	Color int `json:"color"`
	Type  int `json:"type"`
}
type serializedMove struct {
	FromRow  int        `json:"fromRow"`
	FromCol  int        `json:"fromCol"`
	ToRow    int        `json:"toRow"`
	ToCol    int        `json:"toCol"`
	Captures [][2]int   `json:"captures"`
}
type serializedGame struct {
	Board   [10][10]*PieceData `json:"board"`
	Turn    int                `json:"turn"`
	History []serializedMove   `json:"history"`
}

func (g *Game) SaveState(filename string) {
	sb := [10][10]*PieceData{}
	for r := 0; r < 10; r++ {
		for c := 0; c < 10; c++ {
			if p := g.board.grid[r][c]; p != nil {
				sb[r][c] = &PieceData{int(p.Color), int(p.Type)}
			} else {
				sb[r][c] = nil
			}
		}
	}
	hist := []serializedMove{}
	for _, m := range g.moveHistory {
		hist = append(hist, serializedMove{m.FromRow, m.FromCol, m.ToRow, m.ToCol, m.Captures})
	}
	sg := serializedGame{sb, int(g.currentTurn), hist}
	data, _ := json.MarshalIndent(sg, "", "  ")
	ioutil.WriteFile(filename, data, 0644)
}

func (g *Game) LoadState(filename string) {
	data, _ := ioutil.ReadFile(filename)
	var sg serializedGame
	json.Unmarshal(data, &sg)
	board := NewBoard()
	for r := 0; r < 10; r++ {
		for c := 0; c < 10; c++ {
			if sg.Board[r][c] != nil {
				board.grid[r][c] = &Piece{ColorType(sg.Board[r][c].Color), PieceType(sg.Board[r][c].Type)}
			} else {
				board.grid[r][c] = nil
			}
		}
	}
	g.board = board
	g.currentTurn = ColorType(sg.Turn)
	g.moveHistory = []Move{}
	for _, m := range sg.History {
		g.moveHistory = append(g.moveHistory, Move{m.FromRow, m.FromCol, m.ToRow, m.ToCol, m.Captures})
	}
}

func main() {
	rand.Seed(time.Now().UnixNano())
	args := os.Args[1:]
	useColor := true
	twoPlayers := false
	saveFile := ""
	loadFile := ""
	for i := 0; i < len(args); i++ {
		switch args[i] {
		case "--no-color":
			useColor = false
		case "--color":
			useColor = true
		case "--two-players":
			twoPlayers = true
		case "--save":
			if i+1 < len(args) {
				saveFile = args[i+1]
				i++
			}
		case "--load":
			if i+1 < len(args) {
				loadFile = args[i+1]
				i++
			}
		case "--help":
			fmt.Println("Использование: go run checkers.go [опции]")
			fmt.Println("  --color               Цветной вывод (по умолчанию)")
			fmt.Println("  --no-color            Отключить цвет")
			fmt.Println("  --two-players         Режим для двух игроков")
			fmt.Println("  --save <file>         Сохранять состояние")
			fmt.Println("  --load <file>         Загрузить состояние")
			return
		}
	}

	game := NewGame(twoPlayers)
	if loadFile != "" {
		game.LoadState(loadFile)
	}

	scanner := bufio.NewScanner(os.Stdin)

	for {
		game.Display(useColor)
		winner := game.IsGameOver()
		if winner != nil {
			if *winner == WHITE {
				fmt.Println("Победили Белые!")
			} else {
				fmt.Println("Победили Чёрные!")
			}
			return
		}
		if game.twoPlayers {
			name := "Белые"
			if game.currentTurn == BLACK {
				name = "Чёрные"
			}
			fmt.Printf("Ход %s. Введите ход: ", name)
			if !scanner.Scan() {
				return
			}
			input := scanner.Text()
			if input == "quit" || input == "exit" {
				return
			}
			move := game.ParseMove(input)
			if move == nil {
				fmt.Println("Неверный формат хода.")
				continue
			}
			if game.MakeMove(*move) {
				fmt.Println("Ход принят.")
				if saveFile != "" {
					game.SaveState(saveFile)
				}
			} else {
				fmt.Println("Недопустимый ход.")
			}
		} else {
			if game.currentTurn == BLACK {
				move := game.GetAIMove()
				if move == nil {
					fmt.Println("Компьютер не может ходить.")
					return
				}
				game.MakeMove(*move)
				fmt.Printf("Компьютер сходил: %c%d -> %c%d\n", 'A'+move.FromCol, move.FromRow+1, 'A'+move.ToCol, move.ToRow+1)
				if saveFile != "" {
					game.SaveState(saveFile)
				}
			} else {
				fmt.Print("Ваш ход (например, a1 b2): ")
				if !scanner.Scan() {
					return
				}
				input := scanner.Text()
				if input == "quit" || input == "exit" {
					return
				}
				move := game.ParseMove(input)
				if move == nil {
					fmt.Println("Неверный формат хода.")
					continue
				}
				if game.MakeMove(*move) {
					fmt.Println("Ход принят.")
					if saveFile != "" {
						game.SaveState(saveFile)
					}
				} else {
					fmt.Println("Недопустимый ход.")
				}
			}
		}
	}
}
