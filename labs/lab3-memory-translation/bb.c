#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {

    if (argc != 4) {
        printf("Usage: ./bb <base> <bounds> <virtual_address>\n");
        exit(1);
    }

    int base = atoi(argv[1]);
    int bounds = atoi(argv[2]);
    int va = atoi(argv[3]);

    if (va < bounds) {
        printf("Physical address: %d\n", base + va);
    } else {
        printf("Segmentation fault\n");
    }

    return 0;
}