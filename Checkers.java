// Checkers.java
// Версия на Java с использованием рекордов, перечислений, цветного вывода, сохранения/загрузки JSON (Jackson)

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import java.util.stream.*;
import com.fasterxml.jackson.databind.*;

public class Checkers {
    // ANSI
    private static final String RESET = "\u001B[0m";
    private static final String BLACK = "\u001B[30m";
    private static final String RED = "\u001B[31m";
    private static final String GREEN = "\u001B[32m";
    private static final String YELLOW = "\u001B[33m";
    private static final String BLUE = "\u001B[34m";
    private static final String MAGENTA = "\u001B[35m";
    private static final String CYAN = "\u001B[36m";
    private static final String WHITE = "\u001B[37m";
    private static final String BG_BLACK = "\u001B[40m";
    private static final String BG_WHITE = "\u001B[47m";

    private static String colorize(String text, String fg, String bg) {
        return fg + bg + text + RESET;
    }

    enum ColorType { WHITE, BLACK }
    enum PieceType { MAN, KING }

    static class Piece {
        ColorType color;
        PieceType type;
        Piece(ColorType c, PieceType t) { color=c; type=t; }
    }

    static class Move {
        int fromRow, fromCol, toRow, toCol;
        List<int[]> captures;
        Move(int fr, int fc, int tr, int tc, List<int[]> caps) {
            fromRow=fr; fromCol=fc; toRow=tr; toCol=tc; captures=caps;
        }
    }

    static class Board {
        static final int SIZE = 10;
        Piece[][] grid = new Piece[SIZE][SIZE];
        Board() {
            for (int r=0; r<SIZE; r++) {
                for (int c=0; c<SIZE; c++) {
                    if ((r+c)%2==1) {
                        if (r<4) grid[r][c] = new Piece(ColorType.WHITE, PieceType.MAN);
                        else if (r>5) grid[r][c] = new Piece(ColorType.BLACK, PieceType.MAN);
                    }
                }
            }
        }
        boolean inBounds(int r, int c) { return r>=0 && r<SIZE && c>=0 && c<SIZE; }
        Piece getPiece(int r, int c) { return inBounds(r,c) ? grid[r][c] : null; }
        boolean isOccupied(int r, int c) { return getPiece(r,c) != null; }
        void placePiece(int r, int c, Piece p) { grid[r][c] = p; }
        void removePiece(int r, int c) { grid[r][c] = null; }
        List<int[]> findPieces(ColorType color) {
            List<int[]> res = new ArrayList<>();
            for (int r=0; r<SIZE; r++) for (int c=0; c<SIZE; c++) {
                if (grid[r][c] != null && grid[r][c].color == color) res.add(new int[]{r,c});
            }
            return res;
        }
        boolean isKingRow(int r, ColorType color) {
            return (color == ColorType.WHITE && r == SIZE-1) || (color == ColorType.BLACK && r == 0);
        }
        void promoteToKing(int r, int c) {
            Piece p = grid[r][c];
            if (p != null && p.type == PieceType.MAN) grid[r][c] = new Piece(p.color, PieceType.KING);
        }
        Board clone() {
            Board b = new Board();
            for (int r=0; r<SIZE; r++) for (int c=0; c<SIZE; c++) {
                Piece p = grid[r][c];
                b.grid[r][c] = p != null ? new Piece(p.color, p.type) : null;
            }
            return b;
        }
    }

    static class Game {
        Board board;
        ColorType currentTurn;
        boolean twoPlayers;
        List<Move> moveHistory;

        Game(boolean twoPlayers) {
            board = new Board();
            currentTurn = ColorType.WHITE;
            this.twoPlayers = twoPlayers;
            moveHistory = new ArrayList<>();
        }

        ColorType opponent(ColorType c) { return c == ColorType.WHITE ? ColorType.BLACK : ColorType.WHITE; }

        List<Move> getManMoves(int row, int col, ColorType color) {
            List<Move> moves = new ArrayList<>();
            int[][] dirs = color == ColorType.WHITE ? new int[][]{{1,-1},{1,1}} : new int[][]{{-1,-1},{-1,1}};
            for (int[] d : dirs) {
                int nr = row+d[0], nc = col+d[1];
                if (board.inBounds(nr, nc) && !board.isOccupied(nr, nc))
                    moves.add(new Move(row, col, nr, nc, new ArrayList<>()));
            }
            for (int dr : new int[]{-1,1}) for (int dc : new int[]{-1,1}) {
                int nr = row+dr, nc = col+dc;
                if (board.inBounds(nr, nc)) {
                    Piece target = board.getPiece(nr, nc);
                    if (target != null && target.color != color) {
                        int jr = nr+dr, jc = nc+dc;
                        if (board.inBounds(jr, jc) && !board.isOccupied(jr, jc)) {
                            List<int[]> caps = new ArrayList<>();
                            caps.add(new int[]{nr, nc});
                            moves.add(new Move(row, col, jr, jc, caps));
                        }
                    }
                }
            }
            return moves;
        }

        List<Move> getKingMoves(int row, int col, ColorType color) {
            List<Move> moves = new ArrayList<>();
            for (int dr : new int[]{-1,1}) for (int dc : new int[]{-1,1}) {
                int r = row+dr, c = col+dc;
                while (board.inBounds(r, c)) {
                    if (board.isOccupied(r, c)) break;
                    moves.add(new Move(row, col, r, c, new ArrayList<>()));
                    r += dr; c += dc;
                }
                r = row+dr; c = col+dc;
                while (board.inBounds(r, c)) {
                    if (board.isOccupied(r, c)) {
                        Piece target = board.getPiece(r, c);
                        if (target != null && target.color != color) {
                            int br = r+dr, bc = c+dc;
                            while (board.inBounds(br, bc)) {
                                if (board.isOccupied(br, bc)) break;
                                List<int[]> caps = new ArrayList<>();
                                caps.add(new int[]{r, c});
                                moves.add(new Move(row, col, br, bc, caps));
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

        List<Move> getAllValidMoves(ColorType color) {
            List<Move> all = new ArrayList<>();
            for (int[] pos : board.findPieces(color)) {
                int r=pos[0], c=pos[1];
                Piece p = board.getPiece(r, c);
                if (p == null) continue;
                if (p.type == PieceType.MAN) all.addAll(getManMoves(r, c, color));
                else all.addAll(getKingMoves(r, c, color));
            }
            List<Move> caps = all.stream().filter(m -> !m.captures.isEmpty()).collect(Collectors.toList());
            if (!caps.isEmpty()) return caps;
            return all;
        }

        boolean isValidMove(Move move) {
            for (Move m : getAllValidMoves(currentTurn)) {
                if (m.fromRow == move.fromRow && m.fromCol == move.fromCol &&
                    m.toRow == move.toRow && m.toCol == move.toCol) {
                    if (m.captures.size() == move.captures.size()) {
                        Set<String> s1 = m.captures.stream().map(a -> a[0]+","+a[1]).collect(Collectors.toSet());
                        Set<String> s2 = move.captures.stream().map(a -> a[0]+","+a[1]).collect(Collectors.toSet());
                        if (s1.equals(s2)) return true;
                    }
                }
            }
            return false;
        }

        boolean makeMove(Move move) {
            if (!isValidMove(move)) return false;
            Piece p = board.getPiece(move.fromRow, move.fromCol);
            if (p == null) return false;
            board.removePiece(move.fromRow, move.fromCol);
            board.placePiece(move.toRow, move.toCol, p);
            for (int[] cap : move.captures) board.removePiece(cap[0], cap[1]);
            if (board.isKingRow(move.toRow, p.color) && p.type == PieceType.MAN)
                board.promoteToKing(move.toRow, move.toCol);
            moveHistory.add(move);
            currentTurn = opponent(currentTurn);
            return true;
        }

        ColorType isGameOver() {
            if (board.findPieces(ColorType.WHITE).isEmpty()) return ColorType.BLACK;
            if (board.findPieces(ColorType.BLACK).isEmpty()) return ColorType.WHITE;
            if (getAllValidMoves(currentTurn).isEmpty()) return opponent(currentTurn);
            return null;
        }

        Move parseMove(String input) {
            String[] parts = input.trim().split("\\s+");
            if (parts.length < 2) return null;
            List<int[]> coords = new ArrayList<>();
            Pattern pat = Pattern.compile("^([A-Ja-j])([1-9]|10)$");
            for (String p : parts) {
                Matcher m = pat.matcher(p);
                if (!m.matches()) return null;
                int col = m.group(1).toUpperCase().charAt(0) - 'A';
                int row = Integer.parseInt(m.group(2)) - 1;
                coords.add(new int[]{row, col});
            }
            if (coords.size() < 2) return null;
            int[] from = coords.get(0);
            int[] to = coords.get(coords.size()-1);
            List<int[]> captures = new ArrayList<>();
            for (int i=0; i<coords.size()-1; i++) {
                int r1=coords.get(i)[0], c1=coords.get(i)[1];
                int r2=coords.get(i+1)[0], c2=coords.get(i+1)[1];
                if (Math.abs(r2-r1) != Math.abs(c2-c1)) return null;
                int dr = r2>r1 ? 1 : -1;
                int dc = c2>c1 ? 1 : -1;
                int cr = r1+dr, cc = c1+dc;
                while (cr != r2 || cc != c2) {
                    Piece piece = board.getPiece(cr, cc);
                    if (piece == null || piece.color == currentTurn) return null;
                    captures.add(new int[]{cr, cc});
                    cr += dr; cc += dc;
                }
            }
            return new Move(from[0], from[1], to[0], to[1], captures);
        }

        void display(boolean useColor) {
            System.out.print("  ");
            for (int c=0; c<Board.SIZE; c++) System.out.print((char)('A'+c) + " ");
            System.out.println();
            for (int r=Board.SIZE-1; r>=0; r--) {
                System.out.printf("%2d ", r+1);
                for (int c=0; c<Board.SIZE; c++) {
                    Piece p = board.getPiece(r, c);
                    String bg = (r+c)%2==0 ? "white" : "black";
                    if (p == null) {
                        if (useColor) System.out.print(colorize(" . ", RESET, bg.equals("white") ? BG_WHITE : BG_BLACK));
                        else System.out.print(" . ");
                    } else {
                        String sym = p.color == ColorType.WHITE ? "W" : "B";
                        sym += p.type == PieceType.KING ? "*" : " ";
                        String fg = bg.equals("white") ? BLACK : WHITE;
                        if (useColor) System.out.print(colorize(sym, fg, bg.equals("white") ? BG_WHITE : BG_BLACK));
                        else System.out.print(sym + " ");
                    }
                }
                System.out.println();
            }
            System.out.println("Ход: " + (currentTurn == ColorType.WHITE ? "Белые" : "Чёрные"));
        }

        Move getAIMove() {
            List<Move> moves = getAllValidMoves(currentTurn);
            if (moves.isEmpty()) return null;
            List<Move> caps = moves.stream().filter(m -> !m.captures.isEmpty()).collect(Collectors.toList());
            if (!caps.isEmpty()) return caps.get(new Random().nextInt(caps.size()));
            return moves.get(new Random().nextInt(moves.size()));
        }

        // Сохранение и загрузка через Jackson (нужна зависимость)
        void saveState(String filename) throws IOException {
            ObjectMapper mapper = new ObjectMapper();
            // Собираем данные
            Map<String, Object> state = new LinkedHashMap<>();
            // board as list of lists
            List<List<Map<String,Integer>>> boardData = new ArrayList<>();
            for (int r=0; r<Board.SIZE; r++) {
                List<Map<String,Integer>> row = new ArrayList<>();
                for (int c=0; c<Board.SIZE; c++) {
                    Piece p = board.grid[r][c];
                    if (p != null) {
                        Map<String,Integer> pm = new LinkedHashMap<>();
                        pm.put("color", p.color.ordinal());
                        pm.put("type", p.type.ordinal());
                        row.add(pm);
                    } else {
                        row.add(null);
                    }
                }
                boardData.add(row);
            }
            state.put("board", boardData);
            state.put("turn", currentTurn.ordinal());
            List<Map<String,Object>> hist = new ArrayList<>();
            for (Move m : moveHistory) {
                Map<String,Object> hm = new LinkedHashMap<>();
                hm.put("fromRow", m.fromRow); hm.put("fromCol", m.fromCol);
                hm.put("toRow", m.toRow); hm.put("toCol", m.toCol);
                hm.put("captures", m.captures);
                hist.add(hm);
            }
            state.put("history", hist);
            mapper.writerWithDefaultPrettyPrinter().writeValue(new File(filename), state);
        }

        void loadState(String filename) throws IOException {
            ObjectMapper mapper = new ObjectMapper();
            Map<String, Object> state = mapper.readValue(new File(filename), Map.class);
            List<List<Map<String,Integer>>> boardData = (List<List<Map<String,Integer>>>) state.get("board");
            Board b = new Board();
            for (int r=0; r<Board.SIZE; r++) {
                for (int c=0; c<Board.SIZE; c++) {
                    Map<String,Integer> pm = boardData.get(r).get(c);
                    if (pm != null) {
                        b.grid[r][c] = new Piece(ColorType.values()[pm.get("color")], PieceType.values()[pm.get("type")]);
                    } else {
                        b.grid[r][c] = null;
                    }
                }
            }
            this.board = b;
            this.currentTurn = ColorType.values()[(int)state.get("turn")];
            this.moveHistory.clear();
            // history not used
        }
    }

    public static void main(String[] args) throws Exception {
        boolean useColor = true;
        boolean twoPlayers = false;
        String saveFile = null;
        String loadFile = null;
        for (int i=0; i<args.length; i++) {
            if (args[i].equals("--no-color")) useColor = false;
            else if (args[i].equals("--color")) useColor = true;
            else if (args[i].equals("--two-players")) twoPlayers = true;
            else if (args[i].equals("--save") && i+1 < args.length) saveFile = args[++i];
            else if (args[i].equals("--load") && i+1 < args.length) loadFile = args[++i];
            else if (args[i].equals("--help")) {
                System.out.println("Использование: java Checkers [опции]");
                System.out.println("  --color               Цветной вывод (по умолчанию)");
                System.out.println("  --no-color            Отключить цвет");
                System.out.println("  --two-players         Режим для двух игроков");
                System.out.println("  --save <file>         Сохранять состояние");
                System.out.println("  --load <file>         Загрузить состояние");
                return;
            }
        }

        Game game = new Game(twoPlayers);
        if (loadFile != null) game.loadState(loadFile);

        Scanner scanner = new Scanner(System.in);
        while (true) {
            game.display(useColor);
            ColorType winner = game.isGameOver();
            if (winner != null) {
                System.out.println("Победили " + (winner == ColorType.WHITE ? "Белые" : "Чёрные") + "!");
                break;
            }
            if (game.twoPlayers) {
                String name = game.currentTurn == ColorType.WHITE ? "Белые" : "Чёрные";
                System.out.print("Ход " + name + ". Введите ход: ");
                String input = scanner.nextLine();
                if (input.equals("quit") || input.equals("exit")) break;
                Move move = game.parseMove(input);
                if (move == null) {
                    System.out.println("Неверный формат хода.");
                    continue;
                }
                if (game.makeMove(move)) {
                    System.out.println("Ход принят.");
                    if (saveFile != null) game.saveState(saveFile);
                } else {
                    System.out.println("Недопустимый ход.");
                }
            } else {
                if (game.currentTurn == ColorType.BLACK) {
                    Move move = game.getAIMove();
                    if (move == null) {
                        System.out.println("Компьютер не может ходить.");
                        break;
                    }
                    game.makeMove(move);
                    System.out.printf("Компьютер сходил: %c%d -> %c%d\n", 'A'+move.fromCol, move.fromRow+1, 'A'+move.toCol, move.toRow+1);
                    if (saveFile != null) game.saveState(saveFile);
                } else {
                    System.out.print("Ваш ход (например, a1 b2): ");
                    String input = scanner.nextLine();
                    if (input.equals("quit") || input.equals("exit")) break;
                    Move move = game.parseMove(input);
                    if (move == null) {
                        System.out.println("Неверный формат хода.");
                        continue;
                    }
                    if (game.makeMove(move)) {
                        System.out.println("Ход принят.");
                        if (saveFile != null) game.saveState(saveFile);
                    } else {
                        System.out.println("Недопустимый ход.");
                    }
                }
            }
        }
        scanner.close();
    }
}
