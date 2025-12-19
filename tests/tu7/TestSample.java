// Test Java Program for AST Generation
// This program demonstrates various Java language constructs

package com.maestro.test;

import java.util.*;
import java.io.*;

// Interface definition
interface Drawable {
    void draw();
    default void display() {
        System.out.println("Displaying drawable object");
    }
}

// Abstract class
abstract class Shape implements Drawable {
    protected String color;
    protected double area;

    public Shape(String color) {
        this.color = color;
    }

    // Abstract method
    public abstract double calculateArea();

    // Concrete method
    public String getColor() {
        return color;
    }

    @Override
    public void draw() {
        System.out.println("Drawing shape with color: " + color);
    }
}

// Concrete class with inheritance
class Circle extends Shape {
    private double radius;

    public Circle(String color, double radius) {
        super(color);
        this.radius = radius;
    }

    @Override
    public double calculateArea() {
        this.area = Math.PI * radius * radius;
        return this.area;
    }

    public double getRadius() {
        return radius;
    }

    public void setRadius(double radius) {
        this.radius = radius;
    }
}

// Class with multiple interfaces
class Rectangle extends Shape implements Serializable {
    private static final long serialVersionUID = 1L;
    private double width;
    private double height;

    public Rectangle(String color, double width, double height) {
        super(color);
        this.width = width;
        this.height = height;
    }

    @Override
    public double calculateArea() {
        this.area = width * height;
        return this.area;
    }

    public double getWidth() {
        return width;
    }

    public double getHeight() {
        return height;
    }
}

// Enum class
enum Direction {
    NORTH("North"),
    SOUTH("South"),
    EAST("East"),
    WEST("West");

    private final String displayName;

    Direction(String displayName) {
        this.displayName = displayName;
    }

    public String getDisplayName() {
        return displayName;
    }
}

// Generic class
class Container<T> {
    private List<T> items;

    public Container() {
        items = new ArrayList<>();
    }

    public void add(T item) {
        items.add(item);
    }

    public T get(int index) {
        return items.get(index);
    }

    public int size() {
        return items.size();
    }

    // Generic method
    public <U> void printAll(U[] array) {
        for (U item : array) {
            System.out.println(item);
        }
    }
}

// Annotation definition
@interface TestInfo {
    String author() default "Unknown";
    String date();
    int version() default 1;
}

// Inner class example
class OuterClass {
    private int outerValue;

    public OuterClass(int value) {
        this.outerValue = value;
    }

    // Inner class
    class InnerClass {
        private int innerValue;

        public InnerClass(int value) {
            this.innerValue = value;
        }

        public void printValues() {
            System.out.println("Outer: " + outerValue + ", Inner: " + innerValue);
        }
    }

    // Static nested class
    static class StaticNestedClass {
        private int staticValue;

        public StaticNestedClass(int value) {
            this.staticValue = value;
        }

        public void printValue() {
            System.out.println("Static: " + staticValue);
        }
    }
}

// Main class with annotations
@TestInfo(author = "Maestro", date = "2024-12-19", version = 1)
public class TestSample {
    // Static variables
    private static final int MAX_SIZE = 100;
    private static int instanceCount = 0;

    // Instance variables
    private String name;
    private int id;

    // Constructor
    public TestSample(String name, int id) {
        this.name = name;
        this.id = id;
        instanceCount++;
    }

    // Static method
    public static int getInstanceCount() {
        return instanceCount;
    }

    // Instance method
    public void processData(int value) {
        // If-else statement
        if (value > 100) {
            System.out.println("Large value");
        } else if (value > 50) {
            System.out.println("Medium value");
        } else {
            System.out.println("Small value");
        }

        // Switch statement
        switch (value % 3) {
            case 0:
                System.out.println("Divisible by 3");
                break;
            case 1:
                System.out.println("Remainder 1");
                break;
            case 2:
                System.out.println("Remainder 2");
                break;
            default:
                System.out.println("Unknown");
        }

        // For loop
        for (int i = 0; i < value; i++) {
            System.out.print(i + " ");
        }
        System.out.println();

        // Enhanced for loop
        int[] numbers = {1, 2, 3, 4, 5};
        for (int num : numbers) {
            System.out.println(num);
        }

        // While loop
        int counter = 0;
        while (counter < 5) {
            System.out.println("Counter: " + counter);
            counter++;
        }

        // Do-while loop
        int i = 0;
        do {
            System.out.println("Do-while: " + i);
            i++;
        } while (i < 3);

        // Try-catch-finally
        try {
            if (value < 0) {
                throw new IllegalArgumentException("Negative value not allowed");
            }
        } catch (IllegalArgumentException e) {
            System.err.println("Error: " + e.getMessage());
        } finally {
            System.out.println("Cleanup complete");
        }
    }

    // Method with lambda expression
    public void demonstrateLambda() {
        List<String> names = Arrays.asList("Alice", "Bob", "Charlie");

        // Lambda expression
        names.forEach(name -> System.out.println("Hello, " + name));

        // Method reference
        names.forEach(System.out::println);

        // Stream operations
        names.stream()
             .filter(name -> name.startsWith("A"))
             .map(String::toUpperCase)
             .forEach(System.out::println);
    }

    // Main method
    public static void main(String[] args) {
        // Object creation
        Circle circle = new Circle("Red", 5.0);
        System.out.println("Circle area: " + circle.calculateArea());
        circle.draw();

        Rectangle rect = new Rectangle("Blue", 4.0, 6.0);
        System.out.println("Rectangle area: " + rect.calculateArea());

        // Enum usage
        Direction dir = Direction.NORTH;
        System.out.println("Direction: " + dir.getDisplayName());

        // Generic container
        Container<Integer> intContainer = new Container<>();
        intContainer.add(10);
        intContainer.add(20);
        intContainer.add(30);
        System.out.println("Container size: " + intContainer.size());

        // Inner class usage
        OuterClass outer = new OuterClass(100);
        OuterClass.InnerClass inner = outer.new InnerClass(200);
        inner.printValues();

        // Static nested class usage
        OuterClass.StaticNestedClass nested = new OuterClass.StaticNestedClass(300);
        nested.printValue();

        // TestSample instance
        TestSample sample = new TestSample("TestObject", 1);
        sample.processData(75);
        sample.demonstrateLambda();

        System.out.println("Total instances: " + TestSample.getInstanceCount());
    }
}
