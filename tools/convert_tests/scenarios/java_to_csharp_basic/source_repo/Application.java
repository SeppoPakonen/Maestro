import java.util.*;
import java.io.*;

// Main application class demonstrating various Java features
public class Application {
    public static void main(String[] args) {
        System.out.println("Java to C# Conversion Test");
        
        // Create calculator instance
        Calculator calc = new Calculator(10.0);
        System.out.println("Initial value: " + calc.getValue());
        System.out.println("After adding 5: " + calc.add(5).getValue());
        System.out.println("After subtracting 3: " + calc.subtract(3).getValue());
        
        // Test utility functions
        List<String> words = Arrays.asList("hello", "world", "java", "conversion");
        List<Integer> lengths = StringUtils.getLengths(words);
        System.out.println("Word lengths: " + lengths);
        
        // File operations
        try {
            FileHandler.writeStringToFile("test.txt", "Hello, World!");
            String content = FileHandler.readStringFromFile("test.txt");
            System.out.println("File content: " + content);
            
            // Clean up
            new File("test.txt").delete();
        } catch (IOException e) {
            System.err.println("File operation failed: " + e.getMessage());
        }
    }
}

// Calculator class
class Calculator {
    private double value;
    
    public Calculator(double initialValue) {
        this.value = initialValue;
    }
    
    public Calculator add(double number) {
        this.value += number;
        return this;
    }
    
    public Calculator subtract(double number) {
        this.value -= number;
        return this;
    }
    
    public double getValue() {
        return this.value;
    }
}

// Utility classes
class StringUtils {
    public static List<Integer> getLengths(List<String> strings) {
        List<Integer> lengths = new ArrayList<>();
        for (String s : strings) {
            lengths.add(s.length());
        }
        return lengths;
    }
}

class FileHandler {
    public static void writeStringToFile(String filename, String content) throws IOException {
        try (FileWriter writer = new FileWriter(filename)) {
            writer.write(content);
        }
    }
    
    public static String readStringFromFile(String filename) throws IOException {
        StringBuilder content = new StringBuilder();
        try (BufferedReader reader = new BufferedReader(new FileReader(filename))) {
            String line;
            while ((line = reader.readLine()) != null) {
                content.append(line).append("\n");
            }
        }
        return content.toString().trim();
    }
}