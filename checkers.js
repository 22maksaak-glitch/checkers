// checkers.js
// Версия на JavaScript с использованием классов, readline, цветной вывод, сохранение/загрузка (JSON)

const readline = require('readline');
const fs = require('fs');
const { randomInt } = require('crypto');

// Цвета ANSI
const colors = {
    reset: '\x1b[0m',
    black: '\x1b[30m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[34m',
    magenta: '\x1b[35m',
    cyan: '\x1b[36m',
    white: '\x1b[37m',
    bg_black: '\x1b[40m',
    bg_white: '\x1b[47m',
    bg_red: '\x1b[41m',
    bg_green: '\x1b[42m',
    bg_yellow: '\x1b[43m',
    bg_blue: '\x1b[44m',
    bg_magenta: '\x1b[45m',
    bg_cyan: '\x1b[46m',
};

function colorize(text, fg = 'reset', bg = null) {
    const bgCode = bg ? colors[`bg_${bg}`] || '' : '';
    return `${colors[fg] || ''}${bgCode}${text}${colors.reset}`;
}

const ColorType = { WHITE: 1, BLACK: 2 };
const PieceType = { MAN: 1, KING: 2 };

class Piece {
    constructor(color, type) {
        this.color = color;
        this.type = type;
    }
}

class Board {
    static SIZE = 10;
    constructor() {
        this.grid = Array.from({ length: Board.SIZE }, () => Array(Board.SIZE).fill(null));
        this._initBoard();
    }

    _initBoard() {
        for (let r = 0; r < Board.SIZE; r++) {
            for (let c = 0; c < Board.SIZE; c++) {
                if ((r + c) % 2 === 1) {
                    if (r < 4) this.grid[r][c] = new Piece(ColorType.WHITE, PieceType.MAN);
                    else if (r > 5) this.grid[r][c] = new Piece(ColorType.BLACK, PieceType.MAN);
                }
            }
        }
    }

    getPiece(r, c) {
        if (this._inBounds(r, c)) return this.grid[r][c];
        return null;
    }

    _inBounds(r, c) {
        return r >= 0 && r < Board.SIZE && c >= 0 && c < Board.SIZE;
    }

    isOccupied(r, c) {
        return this.getPiece(r, c) !== null;
    }

    placePiece(r, c, piece) {
        this.grid[r][c] = piece;
    }

    removePiece(r, c) {
        this.grid[r][c] = null;
    }

    findPieces(color) {
        const result = [];
        for (let r = 0; r < Board.SIZE; r++) {
            for (let c = 0; c < Board.SIZE; c++) {
                const p = this.grid[r][c];
                if (p && p.color === color) result.push([r, c]);
            }
        }
        return result;
    }

    isKingRow(r, color) {
        return (color === ColorType.WHITE && r === Board.SIZE - 1) ||
               (color === ColorType.BLACK && r === 0);
    }

    promoteToKing(r, c) {
        const p = this.grid[r][c];
        if (p && p.type === PieceType.MAN) {
            this.grid[r][c] = new Piece(p.color, PieceType.KING);
        }
    }

    clone() {
        const b = new Board();
        for (let r = 0; r < Board.SIZE; r++) {
            for (let c = 0; c < Board.SIZE; c++) {
                const p = this.grid[r][c];
                b.grid[r][c] = p ? new Piece(p.color, p.type) : null;
            }
        }
        return b;
    }
}

class Move {
    constructor(fromR, fromC, toR, toC, captures) {
        this.fromRow = fromR;
        this.fromCol = fromC;
        this.toRow = toR;
        this.toCol = toC;
        this.captures = captures || []; // массив [r,c]
    }
}

class CheckersGame {
    constructor(twoPlayers = false) {
        this.board = new Board();
        this.currentTurn = ColorType.WHITE;
        this.twoPlayers = twoPlayers;
        this.moveHistory = [];
    }

    getOpponent(color) {
        return color === ColorType.WHITE ? ColorType.BLACK : ColorType.WHITE;
    }

    getAllValidMoves(color) {
        const pieces = this.board.findPieces(color);
        let moves = [];
        for (const [r, c] of pieces) {
            const piece = this.board.getPiece(r, c);
            if (piece.type === PieceType.MAN) {
                moves = moves.concat(this._getManMoves(r, c, color));
            } else {
                moves = moves.concat(this._getKingMoves(r, c, color));
            }
        }
        // Обязательное взятие
        const captures = moves.filter(m => m.captures.length > 0);
        if (captures.length > 0) return captures;
        return moves;
    }

    _getManMoves(row, col, color) {
        const moves = [];
        const dirs = color === ColorType.WHITE ? [[1,-1],[1,1]] : [[-1,-1],[-1,1]];
        for (const [dr, dc] of dirs) {
            const nr = row + dr, nc = col + dc;
            if (this.board._inBounds(nr, nc) && !this.board.isOccupied(nr, nc)) {
                moves.push(new Move(row, col, nr, nc, []));
            }
        }
        // Взятие (все направления)
        for (const dr of [-1,1]) {
            for (const dc of [-1,1]) {
                const nr = row + dr, nc = col + dc;
                if (this.board._inBounds(nr, nc)) {
                    const target = this.board.getPiece(nr, nc);
                    if (target && target.color !== color) {
                        const jr = nr + dr, jc = nc + dc;
                        if (this.board._inBounds(jr, jc) && !this.board.isOccupied(jr, jc)) {
                            moves.push(new Move(row, col, jr, jc, [[nr, nc]]));
                        }
                    }
                }
            }
        }
        return moves;
    }

    _getKingMoves(row, col, color) {
        const moves = [];
        for (const dr of [-1,1]) {
            for (const dc of [-1,1]) {
                // Обычные ходы
                let r = row + dr, c = col + dc;
                while (this.board._inBounds(r, c)) {
                    if (this.board.isOccupied(r, c)) break;
                    moves.push(new Move(row, col, r, c, []));
                    r += dr; c += dc;
                }
                // Взятия
                r = row + dr; c = col + dc;
                while (this.board._inBounds(r, c)) {
                    if (this.board.isOccupied(r, c)) {
                        const target = this.board.getPiece(r, c);
                        if (target.color !== color) {
                            let br = r + dr, bc = c + dc;
                            while (this.board._inBounds(br, bc)) {
                                if (this.board.isOccupied(br, bc)) break;
                                moves.push(new Move(row, col, br, bc, [[r, c]]));
                                break;
                            }
                        }
                        break;
                    }
                    r += dr; c += dc;
                }
            }
        }
        return moves;
    }

    isValidMove(move) {
        const all = this.getAllValidMoves(this.currentTurn);
        for (const m of all) {
            if (m.fromRow === move.fromRow && m.fromCol === move.fromCol &&
                m.toRow === move.toRow && m.toCol === move.toCol) {
                // Сравниваем captures (независимо от порядка)
                if (m.captures.length === move.captures.length) {
                    const set1 = new Set(m.captures.map(([r,c]) => `${r},${c}`));
                    const set2 = new Set(move.captures.map(([r,c]) => `${r},${c}`));
                    if (set1.size === set2.size && [...set1].every(k => set2.has(k))) {
                        return true;
                    }
                }
            }
        }
        return false;
    }

    makeMove(move) {
        if (!this.isValidMove(move)) return false;
        const piece = this.board.getPiece(move.fromRow, move.fromCol);
        if (!piece) return false;
        this.board.removePiece(move.fromRow, move.fromCol);
        this.board.placePiece(move.toRow, move.toCol, piece);
        for (const [r, c] of move.captures) {
            this.board.removePiece(r, c);
        }
        if (this.board.isKingRow(move.toRow, piece.color) && piece.type === PieceType.MAN) {
            this.board.promoteToKing(move.toRow, move.toCol);
        }
        this.moveHistory.push(move);
        this.currentTurn = this.getOpponent(this.currentTurn);
        return true;
    }

    isGameOver() {
        const white = this.board.findPieces(ColorType.WHITE);
        const black = this.board.findPieces(ColorType.BLACK);
        if (white.length === 0) return ColorType.BLACK;
        if (black.length === 0) return ColorType.WHITE;
        const moves = this.getAllValidMoves(this.currentTurn);
        if (moves.length === 0) return this.getOpponent(this.currentTurn);
        return null;
    }

    parseMove(input) {
        const parts = input.trim().split(/\s+/);
        if (parts.length < 2) return null;
        const coords = [];
        for (const p of parts) {
            const m = p.match(/^([A-Ja-j])([1-9]|10)$/);
            if (!m) return null;
            const col = m[1].toUpperCase().charCodeAt(0) - 'A'.charCodeAt(0);
            const row = parseInt(m[2]) - 1;
            coords.push([row, col]);
        }
        if (coords.length < 2) return null;
        const from = coords[0];
        const to = coords[coords.length - 1];
        const captures = [];
        for (let i = 0; i < coords.length - 1; i++) {
            const [r1, c1] = coords[i];
            const [r2, c2] = coords[i+1];
            if (Math.abs(r2-r1) !== Math.abs(c2-c1)) return null;
            const dr = r2 > r1 ? 1 : -1;
            const dc = c2 > c1 ? 1 : -1;
            let cr = r1 + dr, cc = c1 + dc;
            while (cr !== r2 || cc !== c2) {
                const piece = this.board.getPiece(cr, cc);
                if (!piece || piece.color === this.currentTurn) return null;
                captures.push([cr, cc]);
                cr += dr; cc += dc;
            }
        }
        return new Move(from[0], from[1], to[0], to[1], captures);
    }

    display(useColor = true) {
        const size = Board.SIZE;
        console.log('  ' + Array.from({length: size}, (_,i) => String.fromCharCode(65+i)).join(' '));
        for (let r = size - 1; r >= 0; r--) {
            const label = (r+1).toString().padStart(2, ' ');
            process.stdout.write(label + ' ');
            for (let c = 0; c < size; c++) {
                const piece = this.board.getPiece(r, c);
                const bg = (r + c) % 2 === 0 ? 'white' : 'black';
                if (!piece) {
                    if (useColor) {
                        process.stdout.write(colorize(' . ', 'reset', bg));
                    } else {
                        process.stdout.write(' . ');
                    }
                } else {
                    const symbol = piece.color === ColorType.WHITE ? 'W' : 'B';
                    const type = piece.type === PieceType.KING ? '*' : ' ';
                    const fg = bg === 'white' ? 'black' : 'white';
                    if (useColor) {
                        process.stdout.write(colorize(symbol + type, fg, bg));
                    } else {
                        process.stdout.write(symbol + type + ' ');
                    }
                }
            }
            console.log();
        }
        console.log(`Ход: ${this.currentTurn === ColorType.WHITE ? 'Белые' : 'Чёрные'}`);
    }

    getAIMove() {
        const moves = this.getAllValidMoves(this.currentTurn);
        if (moves.length === 0) return null;
        const captures = moves.filter(m => m.captures.length > 0);
        if (captures.length > 0) return captures[randomInt(captures.length)];
        return moves[randomInt(moves.length)];
    }

    saveState(filename) {
        const state = {
            board: this.board.grid.map(row => row.map(p => p ? {color: p.color, type: p.type} : null)),
            turn: this.currentTurn,
            history: this.moveHistory.map(m => ({fromRow: m.fromRow, fromCol: m.fromCol, toRow: m.toRow, toCol: m.toCol, captures: m.captures}))
        };
        fs.writeFileSync(filename, JSON.stringify(state, null, 2));
    }

    loadState(filename) {
        const data = JSON.parse(fs.readFileSync(filename, 'utf-8'));
        const board = new Board();
        for (let r = 0; r < Board.SIZE; r++) {
            for (let c = 0; c < Board.SIZE; c++) {
                const pData = data.board[r][c];
                board.grid[r][c] = pData ? new Piece(pData.color, pData.type) : null;
            }
        }
        this.board = board;
        this.currentTurn = data.turn;
        this.moveHistory = data.history.map(h => new Move(h.fromRow, h.fromCol, h.toRow, h.toCol, h.captures));
    }
}

function main() {
    const args = process.argv.slice(2);
    let useColor = true;
    let twoPlayers = false;
    let saveFile = null;
    let loadFile = null;
    for (let i = 0; i < args.length; i++) {
        if (args[i] === '--no-color') useColor = false;
        else if (args[i] === '--color') useColor = true;
        else if (args[i] === '--two-players') twoPlayers = true;
        else if (args[i] === '--save' && i+1 < args.length) saveFile = args[++i];
        else if (args[i] === '--load' && i+1 < args.length) loadFile = args[++i];
    }

    const game = new CheckersGame(twoPlayers);
    if (loadFile) game.loadState(loadFile);

    const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout
    });

    function promptMove() {
        game.display(useColor);
        const winner = game.isGameOver();
        if (winner) {
            console.log(`Победили ${winner === ColorType.WHITE ? 'Белые' : 'Чёрные'}!`);
            rl.close();
            return;
        }
        if (game.twoPlayers) {
            const name = game.currentTurn === ColorType.WHITE ? 'Белые' : 'Чёрные';
            rl.question(`Ход ${name}. Введите ход: `, handleInput);
        } else {
            if (game.currentTurn === ColorType.BLACK) {
                // Компьютер
                const move = game.getAIMove();
                if (move) {
                    game.makeMove(move);
                    console.log(`Компьютер сходил: ${String.fromCharCode(65+move.fromCol)}${move.fromRow+1} -> ${String.fromCharCode(65+move.toCol)}${move.toRow+1}`);
                    if (saveFile) game.saveState(saveFile);
                    promptMove();
                } else {
                    console.log('Компьютер не может ходить.');
                    rl.close();
                }
            } else {
                rl.question('Ваш ход (например, a1 b2): ', handleInput);
            }
        }
    }

    function handleInput(input) {
        if (input.toLowerCase() === 'quit' || input.toLowerCase() === 'exit') {
            rl.close();
            return;
        }
        const move = game.parseMove(input);
        if (!move) {
            console.log('Неверный формат хода.');
            promptMove();
            return;
        }
        if (game.makeMove(move)) {
            console.log('Ход принят.');
            if (saveFile) game.saveState(saveFile);
            promptMove();
        } else {
            console.log('Недопустимый ход.');
            promptMove();
        }
    }

    promptMove();
}

if (require.main === module) {
    main();
}
