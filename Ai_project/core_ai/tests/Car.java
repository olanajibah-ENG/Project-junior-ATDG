public class Car {
    private String model;
    private Engine engine;

    public Car(String model) {
        this.model = model;
        this.engine = new Engine(200);
    }

    public void drive() {
        System.out.println("Driving " + model + " with " + engine.getHorsepower() + " HP engine");
    }
}
