// Checkers.cs
// Версия на C# с использованием record, enum, LINQ, цветного вывода, сохранения/загрузки JSON

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;

namespace Checkers
{
    // ANSI
    public static class Ansi
    {
        public const string Reset = "\x1b[0m";
        public const string Black = "\x1b[30m";
        public const string Red = "\x1b[31m";
        public const string Green = "\x1b[32m";
        public const string Yellow = "\x1b[33m";
        public const string Blue = "\x1b[34m";
        public const string Magenta = "\x1b[35m";
        public const string Cyan = "\x1b[36m";
        public const string White = "\x1b[37m";
        public const string BgBlack = "\x1b[40m";
        public const string BgWhite = "\x1b[47m";

        public static string Colorize(string text, string fg = Reset, string bg = "")
        {
            return fg + bg + text + Reset;
        }
    }

    public enum ColorType { WHITE, BLACK }
    public enum PieceType { MAN, KING }

    public record Piece(ColorType Color, PieceType Type);

    public record Move(int FromRow, int FromCol, int ToRow, int ToCol, List<(int,int)> Captures);

    public class Board
    {
        public const int Size = 10;
        public Piece?[,] Grid = new Piece[Size, Size];

        public Board()
        {
            for (int r = 0; r < Size; r++)
                for (int c = 0; c < Size; c++)
                    if ((r + c) % 2 == 1)
                    {
                        if (r < 4) Grid[r, c] = new Piece(ColorType.WHITE, PieceType.MAN);
                        else if (r > 5) Grid[r, c] = new Piece(ColorType.BLACK, PieceType.MAN);
                    }
        }

        public bool InBounds(int r, int c) => r >= 0 && r < Size && c >= 0 && c < Size;
        public Piece? GetPiece(int r, int c) => InBounds(r, c) ? Grid[r, c] : null;
        public bool IsOccupied(int r, int c) => GetPiece(r, c) != null;
        public void PlacePiece(int r, int c, Piece p) => Grid[r, c] = p;
        public void RemovePiece(int r, int c) => Grid[r, c] = null;
        public List<(int,int)> FindPieces(ColorType color)
        {
            var res = new List<(int,int)>();
            for (int r = 0; r < Size; r++)
                for (int c = 0; c < Size; c++)
                    if (Grid[r, c]?.Color == color)
                        res.Add((r, c));
            return res;
        }
        public bool IsKingRow(int r, ColorType color) =>
            (color == ColorType.WHITE && r == Size - 1) || (color == ColorType.BLACK && r == 0);
        public void PromoteToKing(int r, int c)
        {
            var p = Grid[r, c];
            if (p != null && p.Type == PieceType.MAN)
                Grid[r, c] = new Piece(p.Color, PieceType.KING);
        }
        public Board Clone()
        {
            var b = new Board();
            for (int r = 0; r < Size; r++)
                for (int c = 0; c < Size; c++)
                    b.Grid[r, c] = Grid[r, c] != null ? new Piece(Grid[r, c].Color, Grid[r, c].Type) : null;
            return b;
        }
    }

    public class Game
    {
        public Board Board { get; private set; }
        public ColorType CurrentTurn { get; private set; }
        public bool TwoPlayers { get; }
        public List<Move> MoveHistory { get; } = new();

        public Game(bool twoPlayers)
        {
            Board = new Board();
            CurrentTurn = ColorType.WHITE;
            TwoPlayers = twoPlayers;
        }

        private ColorType Opponent(ColorType c) => c == ColorType.WHITE ? ColorType.BLACK : ColorType.WHITE;

        private IEnumerable<Move> GetManMoves(int row, int col, ColorType color)
        {
            var moves = new List<Move>();
            var dirs = color == ColorType.WHITE ? new (int,int)[]{(1,-1),(1,1)} : new (int,int)[]{(-1,-1),(-1,1)};
            foreach (var (dr,dc) in dirs)
            {
                int nr = row+dr, nc = col+dc;
                if (Board.InBounds(nr,nc) && !Board.IsOccupied(nr,nc))
                    moves.Add(new Move(row,col,nr,nc,new List<(int,int)>()));
            }
            foreach (int dr in new[]{-1,1})
                foreach (int dc in new[]{-1,1})
                {
                    int nr = row+dr, nc = col+dc;
                    if (Board.InBounds(nr,nc))
                    {
                        var target = Board.GetPiece(nr,nc);
                        if (target != null && target.Color != color)
                        {
                            int jr = nr+dr, jc = nc+dc;
                            if (Board.InBounds(jr,jc) && !Board.IsOccupied(jr,jc))
                                moves.Add(new Move(row,col,jr,jc,new List<(int,int)>{(nr,nc)}));
                        }
                    }
                }
            return moves;
        }

        private IEnumerable<Move> GetKingMoves(int row, int col, ColorType color)
        {
            var moves = new List<Move>();
            foreach (int dr in new[]{-1,1})
                foreach (int dc in new[]{-1,1})
                {
                    int r = row+dr, c = col+dc;
                    while (Board.InBounds(r,c))
                    {
                        if (Board.IsOccupied(r,c)) break;
                        moves.Add(new Move(row,col,r,c,new List<(int,int)>()));
                        r += dr; c += dc;
                    }
                    r = row+dr; c = col+dc;
                    while (Board.InBounds(r,c))
                    {
                        if (Board.IsOccupied(r,c))
                        {
                            var target = Board.GetPiece(r,c);
                            if (target != null && target.Color != color)
                            {
                                int br = r+dr, bc = c+dc;
                                while (Board.InBounds(br,bc))
                                {
                                    if (Board.IsOccupied(br,bc)) break;
                                    moves.Add(new Move(row,col,br,bc,new List<(int,int)>{(r,c)}));
                                    break;
                                }
                            }
                            break;
                        }
                        r += dr; c += dc;
                    }
                }
            return moves;
        }

        public List<Move> GetAllValidMoves(ColorType color)
        {
            var all = new List<Move>();
            foreach (var (r,c) in Board.FindPieces(color))
            {
                var p = Board.GetPiece(r,c);
                if (p == null) continue;
                if (p.Type == PieceType.MAN) all.AddRange(GetManMoves(r,c,color));
                else all.AddRange(GetKingMoves(r,c,color));
            }
            var caps = all.Where(m => m.Captures.Count > 0).ToList();
            if (caps.Count > 0) return caps;
            return all;
        }

        public bool IsValidMove(Move move)
        {
            foreach (var m in GetAllValidMoves(CurrentTurn))
            {
                if (m.FromRow == move.FromRow && m.FromCol == move.FromCol &&
                    m.ToRow == move.ToRow && m.ToCol == move.ToCol)
                {
                    if (m.Captures.Count == move.Captures.Count)
                    {
                        var s1 = new HashSet<string>(m.Captures.Select(t => $"{t.Item1},{t.Item2}"));
                        var s2 = new HashSet<string>(move.Captures.Select(t => $"{t.Item1},{t.Item2}"));
                        if (s1.SetEquals(s2)) return true;
                    }
                }
            }
            return false;
        }

        public bool MakeMove(Move move)
        {
            if (!IsValidMove(move)) return false;
            var p = Board.GetPiece(move.FromRow, move.FromCol);
            if (p == null) return false;
            Board.RemovePiece(move.FromRow, move.FromCol);
            Board.PlacePiece(move.ToRow, move.ToCol, p);
            foreach (var (r,c) in move.Captures)
                Board.RemovePiece(r,c);
            if (Board.IsKingRow(move.ToRow, p.Color) && p.Type == PieceType.MAN)
                Board.PromoteToKing(move.ToRow, move.ToCol);
            MoveHistory.Add(move);
            CurrentTurn = Opponent(CurrentTurn);
            return true;
        }

        public ColorType? IsGameOver()
        {
            if (Board.FindPieces(ColorType.WHITE).Count == 0) return ColorType.BLACK;
            if (Board.FindPieces(ColorType.BLACK).Count == 0) return ColorType.WHITE;
            if (GetAllValidMoves(CurrentTurn).Count == 0) return Opponent(CurrentTurn);
            return null;
        }

        public Move? ParseMove(string input)
        {
            var parts = input.Trim().Split(' ', StringSplitOptions.RemoveEmptyEntries);
            if (parts.Length < 2) return null;
            var coords = new List<(int,int)>();
            var re = new Regex(@"^([A-Ja-j])([1-9]|10)$");
            foreach (var p in parts)
            {
                var m = re.Match(p);
                if (!m.Success) return null;
                int col = char.ToUpper(m.Groups[1].Value[0]) - 'A';
                int row = int.Parse(m.Groups[2].Value) - 1;
                coords.Add((row, col));
            }
            if (coords.Count < 2) return null;
            var from = coords[0];
            var to = coords[^1];
            var captures = new List<(int,int)>();
            for (int i=0; i<coords.Count-1; i++)
            {
                var (r1,c1) = coords[i];
                var (r2,c2) = coords[i+1];
                if (Math.Abs(r2-r1) != Math.Abs(c2-c1)) return null;
                int dr = r2>r1 ? 1 : -1;
                int dc = c2>c1 ? 1 : -1;
                int cr = r1+dr, cc = c1+dc;
                while (cr != r2 || cc != c2)
                {
                    var piece = Board.GetPiece(cr, cc);
                    if (piece == null || piece.Color == CurrentTurn) return null;
                    captures.Add((cr, cc));
                    cr += dr; cc += dc;
                }
            }
            return new Move(from.Item1, from.Item2, to.Item1, to.Item2, captures);
        }

        public void Display(bool useColor)
        {
            Console.Write("  ");
            for (int c=0; c<Board.Size; c++) Console.Write($"{(char)('A'+c)} ");
            Console.WriteLine();
            for (int r=Board.Size-1; r>=0; r--)
            {
                Console.Write($"{r+1,2} ");
                for (int c=0; c<Board.Size; c++)
                {
                    var p = Board.GetPiece(r,c);
                    string bg = (r+c)%2==0 ? "white" : "black";
                    if (p == null)
                    {
                        if (useColor) Console.Write(Ansi.Colorize(" . ", Ansi.Reset, bg=="white" ? Ansi.BgWhite : Ansi.BgBlack));
                        else Console.Write(" . ");
                    }
                    else
                    {
                        string sym = p.Color == ColorType.WHITE ? "W" : "B";
                        sym += p.Type == PieceType.KING ? "*" : " ";
                        string fg = bg=="white" ? Ansi.Black : Ansi.White;
                        if (useColor) Console.Write(Ansi.Colorize(sym, fg, bg=="white" ? Ansi.BgWhite : Ansi.BgBlack));
                        else Console.Write(sym + " ");
                    }
                }
                Console.WriteLine();
            }
            Console.WriteLine($"Ход: {(CurrentTurn == ColorType.WHITE ? "Белые" : "Чёрные")}");
        }

        public Move? GetAIMove()
        {
            var moves = GetAllValidMoves(CurrentTurn);
            if (moves.Count == 0) return null;
            var caps = moves.Where(m => m.Captures.Count > 0).ToList();
            if (caps.Count > 0) return caps[new Random().Next(caps.Count)];
            return moves[new Random().Next(moves.Count)];
        }

        public void SaveState(string filename)
        {
            var state = new
            {
                board = Enumerable.Range(0, Board.Size).Select(r =>
                    Enumerable.Range(0, Board.Size).Select(c =>
                        Board.Grid[r,c] != null ? new { color = Board.Grid[r,c].Color.ToString(), type = Board.Grid[r,c].Type.ToString() } : null
                    ).ToArray()
                ).ToArray(),
                turn = CurrentTurn.ToString(),
                history = MoveHistory.Select(m => new { m.FromRow, m.FromCol, m.ToRow, m.ToCol, Captures = m.Captures.Select(t => new { t.Item1, t.Item2 }).ToArray() }).ToArray()
            };
            var json = JsonSerializer.Serialize(state, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(filename, json);
        }

        public void LoadState(string filename)
        {
            var json = File.ReadAllText(filename);
            var state = JsonSerializer.Deserialize<JsonElement>(json);
            var boardData = state.GetProperty("board").EnumerateArray().Select(row => row.EnumerateArray().Select(cell =>
                cell.ValueKind != JsonValueKind.Null ? new Piece(
                    Enum.Parse<ColorType>(cell.GetProperty("color").GetString()),
                    Enum.Parse<PieceType>(cell.GetProperty("type").GetString())
                ) : null
            ).ToArray()).ToArray();
            var b = new Board();
            for (int r=0; r<Board.Size; r++)
                for (int c=0; c<Board.Size; c++)
                    b.Grid[r,c] = boardData[r][c];
            Board = b;
            CurrentTurn = Enum.Parse<ColorType>(state.GetProperty("turn").GetString());
            // history не восстанавливаем
        }
    }

    class Program
    {
        static void Main(string[] args)
        {
            bool useColor = true;
            bool twoPlayers = false;
            string saveFile = null, loadFile = null;
            for (int i=0; i<args.Length; i++)
            {
                if (args[i] == "--no-color") useColor = false;
                else if (args[i] == "--color") useColor = true;
                else if (args[i] == "--two-players") twoPlayers = true;
                else if (args[i] == "--save" && i+1 < args.Length) saveFile = args[++i];
                else if (args[i] == "--load" && i+1 < args.Length) loadFile = args[++i];
                else if (args[i] == "--help")
                {
                    Console.WriteLine("Использование: dotnet run -- [опции]");
                    Console.WriteLine("  --color               Цветной вывод (по умолчанию)");
                    Console.WriteLine("  --no-color            Отключить цвет");
                    Console.WriteLine("  --two-players         Режим для двух игроков");
                    Console.WriteLine("  --save <file>         Сохранять состояние");
                    Console.WriteLine("  --load <file>         Загрузить состояние");
                    return;
                }
            }

            var game = new Game(twoPlayers);
            if (loadFile != null) game.LoadState(loadFile);

            while (true)
            {
                game.Display(useColor);
                var winner = game.IsGameOver();
                if (winner != null)
                {
                    Console.WriteLine($"Победили {(winner == ColorType.WHITE ? "Белые" : "Чёрные")}!");
                    break;
                }
                if (game.TwoPlayers)
                {
                    string name = game.CurrentTurn == ColorType.WHITE ? "Белые" : "Чёрные";
                    Console.Write($"Ход {name}. Введите ход: ");
                    string input = Console.ReadLine();
                    if (input == "quit" || input == "exit") break;
                    var move = game.ParseMove(input);
                    if (move == null) { Console.WriteLine("Неверный формат хода."); continue; }
                    if (game.MakeMove(move))
                    {
                        Console.WriteLine("Ход принят.");
                        if (saveFile != null) game.SaveState(saveFile);
                    }
                    else Console.WriteLine("Недопустимый ход.");
                }
                else
                {
                    if (game.CurrentTurn == ColorType.BLACK)
                    {
                        var move = game.GetAIMove();
                        if (move == null) { Console.WriteLine("Компьютер не может ходить."); break; }
                        game.MakeMove(move);
                        Console.WriteLine($"Компьютер сходил: {(char)('A'+move.FromCol)}{move.FromRow+1} -> {(char)('A'+move.ToCol)}{move.ToRow+1}");
                        if (saveFile != null) game.SaveState(saveFile);
                    }
                    else
                    {
                        Console.Write("Ваш ход (например, a1 b2): ");
                        string input = Console.ReadLine();
                        if (input == "quit" || input == "exit") break;
                        var move = game.ParseMove(input);
                        if (move == null) { Console.WriteLine("Неверный формат хода."); continue; }
                        if (game.MakeMove(move))
                        {
                            Console.WriteLine("Ход принят.");
                            if (saveFile != null) game.SaveState(saveFile);
                        }
                        else Console.WriteLine("Недопустимый ход.");
                    }
                }
            }
        }
    }
}
